# -*- coding: utf-8 -*-
"""
EPMT Outliers API
=================

The EPMT Outliers API provides functions to determine outliers
among a collection of jobs, operations or processes. It uses
EPMT Query API and the EPMT statistics module for the underlying 
operations.

Most functions in this API deal with dataframes and understand
high-level primitives such as jobs and processes.
"""


from __future__ import print_function
import pandas as pd
import numpy as np
from logging import getLogger
from json import dumps, loads
from orm import db_session, ReferenceModel, orm_get, orm_col_len

# the first epmt import must be epmt_query as it sets up logging
import epmt_query as eq
from epmtlib import tags_list, tag_from_string, dict_in_list
from epmt_stat import thresholds, outliers_iqr, outliers_modified_z_score, rca, get_classifier_name, is_classifier_mv, partition_classifiers_uv_mv, mvod_scores_using_model, uvod_classifiers, modified_z_score

logger = getLogger(__name__)  # you can use other name
import epmt_settings as settings

FEATURES = settings.outlier_features


def partition_jobs(jobs, features=FEATURES, methods=[], thresholds=thresholds):
    """
    Partition jobs into disjoint sets of reference and outliers::Outlier Detection

    Parameters
    ----------
          jobs : list of strings or list of Job objects or ORM query
                 The collection of jobs to partition

      features : list of strings or '*', optional
                 Partitioning is done on the basis of these features
                 The wildcard -- '*' -- or an empty feature list means
                 use all features

       methods : list of callables, optional
                 If unset, a default list of univariate classifiers is used

    thresholds : dict, optional
                 Defines the thresholds for different classifiers.
                 This is used from settings, and ordinarily you should
                 not have to manually use this option

    Returns
    -------
    A dict where the keys are feature strings and the values are
    tuples containing the two disjoint sets -- reference jobs and
    outlier jobs
 
    Examples
    -------- 
    >> parts = eod.partition_jobs(jobs, methods = [es.modified_z_score])
    >>> pprint(parts)
    {'cpu_time': (set([u'kern-6656-20190614-190245',
                   u'kern-6656-20190614-194024',
                   u'kern-6656-20190614-191138']),
                  set([u'kern-6656-20190614-192044-outlier'])),
     'duration': (set([u'kern-6656-20190614-190245',
                   u'kern-6656-20190614-194024',
                   u'kern-6656-20190614-191138']),
                  set([u'kern-6656-20190614-192044-outlier'])),
     'num_procs': (set([u'kern-6656-20190614-190245',
                    u'kern-6656-20190614-192044-outlier',
                    u'kern-6656-20190614-194024',
                    u'kern-6656-20190614-191138']),
                   set([]))}
    """
    (_,parts) = detect_outlier_jobs(jobs, features=features, methods=methods, thresholds=thresholds)
    return parts


def partition_jobs_by_ops(jobs, tags=[], features=FEATURES, methods=[modified_z_score], thresholds=thresholds):
    """
    Partitions operations into disjoint sets of reference and outliers::Outlier Detection

    
    Parameters
    ----------
          jobs : list of strings or list of Job objects or ORM query
                 The collection of jobs whose operations will be partitioned
          tags : list of strings or list of dicts or string, optional
                 The tags define the operations which will be partitioned.
                 If not specified the unique process tags across all jobs
                 will be used
      features : list of strings, optional
                 Defaults to the features defined in settings

       methods : list of callables, optional
                 One or more methods for outlier detection.
                 Defaults to MADZ

    thresholds : dict, optional
                 Defines the thresholds for different classifiers.
                 This is used from settings, and ordinarily you should
                 not have to manually use this option
    
    Returns
    -------
       dictionary where each key is a tag, and the value is a tuple like 
       ([ref_jobs],[outlier_jobs).
    
    Notes
    -----
    This function partitions the supplied jobs into two partitions:
    reference jobs and outliers. The partitioning is done for each tag, and
    for a tag, if any feature makes a job an outlier then it's put in the
    outlier partition.
    
    Examples
    --------
    >>> jobs = eq.get_jobs(tags = 'exp_name:linux_kernel', fmt='terse)
    >>> parts = eod.partition_jobs_by_ops(jobs, methods = [es.modified_z_score])
    >>> pprint(parts)
    {'{"op_instance": "1", "op_sequence": "1", "op": "download"}': (set[u'kern-6656-20190614-190245',
                                                                     u'kern-6656-20190614-191138',
                                                                     u'kern-6656-20190614-194024']),
                                                               set[u'kern-6656-20190614-192044-outlier'])),
     '{"op_instance": "2", "op_sequence": "2", "op": "extract"}': (set([u'kern-6656-20190614-190245',
                                                                    u'kern-6656-20190614-191138',
                                                                    u'kern-6656-20190614-194024']),
                                                               set([u'kern-6656-20190614-192044-outlier'])),
    ...
    }
    
    
    In the example above we did not supply any tags so the set of unique
    process tags was determined automatically. We can also choose to
    specify a tag (or a list of tags) as so:
    >>> parts = eod.partition_jobs_by_ops(jobs, tags = 'op:build;op_instance:4;op_sequence:4', methods = [es.modified_z_score])
    >>> pprint(parts)
    {'{"op_instance": "4", "op_sequence": "4", "op": "build"}': (set([u'kern-6656-20190614-190245',
                                                                  u'kern-6656-20190614-191138',
                                                                  u'kern-6656-20190614-194024']),
                                                              set([u'kern-6656-20190614-192044-outlier']))}
    """
    (_, parts, _, _, _) = detect_outlier_ops(jobs, tags=tags, features=features, methods=methods, thresholds=thresholds)
    return parts


@db_session
def detect_outlier_jobs(jobs, trained_model=None, features = FEATURES, methods=[], thresholds = thresholds, sanity_check=True, pca = False):
    """
    Detects outlier jobs::Outlier Detection

    This function will detects outlier jobs among a set of input jobs.
    This should be used as the first tool in outlier detection. If you
    would like to dig deeper into the operations that are outliers,
    then use `detect_outlier_ops`, which will take appreciably longer
    than this function.
    
    Parameters
    ----------

          jobs : list of strings or list of objects or ORM query or dataframe
                 You need a minimum of 4 jobs without a trained model for
                 outlier detection

 trained_model : int, optional
                 The ID of a reference model. If not specified,
                 outlier detection will be done from within the jobs

    features   : list of strings or '*', optional
                 List of features to use for outlier detection. 
                 An empty list or '*' means use all available features.
                 Defaults to a list specified in settings

       methods : list of callables, optional 
                 This is an advanced option to specify the function(s) to use
                 for outlier detection. If unspecified it will default to
                 all the available univariate classifiers
                 If multivariate classifiers are specified, a trained model 
                 *must* be specified. We only support pyod classifiers at present 
                 for multivariate classifiers. Do not mix univariate and 
                 multivariate classifiers.

    thresholds : dict, optional
                 Defines the thresholds for different classifiers.
                 This is used from settings, and ordinarily you should
                 not have to manually use this option

  sanity_check : boolean, optional
                 Warn if the jobs are not comparable. Enabled by default.

           pca : boolean or int or float, optional
                 False by default. If enabled, the PCA analysis will be done
                 on the features prior to outlier detection. Rather than setting
                 this option to True, you may also set this option to something
                 like: pca = 2, in which case it will mean you want two components
                 in the PCA. Or something like, pca = 0.95, which will be 
                 intepreted as meaning do PCA and automatically select the number
                 components to arrive at the number of components in the PCA.
                 If set to True, a 0.85 variance ratio will be set to enable
                 automatic selection of PCA components.
    
    Returns
    -------
      The output of the function depends on the classifier methods
      given as argument to the function:

      If univariate classifiers are used or if no classifiers
      are given: (uv_df, uv_dict)
        uv_df: Is a dataframe like shown below (univariate classifier examples)
      uv_dict: Is a  dictionary indexed by one of the requested "features"
               and the value is a tuple like ([ref_jobs], [outlier_jobs])

      If only multivariate classifiers are used: mv_df, mv_dict
         mv_df: Is a dataframe containing outlier scores for given
               jobs. A higher score indications more classifier
               methods classified the job as an outlier.

      mv_dict: Is a dictionary indexed by classifier name, and
               contains the outlier vector generated by classification
               using said classifier.

    Notes
    -----
    You cannot mix UV classifiers with MV classifiers. You MUST specify
    either only univariate classifiers, or only multivariate classifiers.
    
    
    Examples
    --------

    The following examples show OD using UV classifiers:

    >>> jobs = eq.get_jobs(fmt='orm', tags='exp_name:linux_kernel') 
    >>> len(jobs)
    4
    >>> (df, parts) = eod.detect_outlier_jobs(jobs, methods=[es.modified_z_score])
    >>> df
                                   jobid  duration  cpu_time  num_procs
    0          kern-6656-20190614-190245         0         0          0
    1  kern-6656-20190614-192044-outlier         1         1          0
    2          kern-6656-20190614-194024         0         0          0
    3          kern-6656-20190614-191138         0         0          0
    
    >>> pprint(parts)
    {'cpu_time': ([u'kern-6656-20190614-190245',
                   u'kern-6656-20190614-194024',
                   u'kern-6656-20190614-191138'],
                  [u'kern-6656-20190614-192044-outlier']),
     'duration': ([u'kern-6656-20190614-190245',
                   u'kern-6656-20190614-194024',
                   u'kern-6656-20190614-191138'],
                  [u'kern-6656-20190614-192044-outlier']),
     'num_procs': ([u'kern-6656-20190614-190245',
                    u'kern-6656-20190614-192044-outlier',
                    u'kern-6656-20190614-194024',
                    u'kern-6656-20190614-191138'],
                   [])}


    # Now let's look at outlier detection using PCA. Here we do
    # with 2 PCA components. We could instead have set a variance
    # ratio, such as 0.90. In which case, the number of PCA components
    # would have been automatically determined.
    # Notice, we select all available features as input to the PCA engine.
    # We scale the PCA scores since the PCA features aren't equal. So,
    # the column of importance is 'pca_weighted', rather than the individual
    # pca columns. 

    >>> x = eod.detect_outlier_jobs(eq.get_jobs(fmt='pandas'), features=[], pca = 2, methods=[es.modified_z_score])
           INFO: epmt_outliers: outlier detection provided 1 classifiers
           INFO: epmt_outliers: 1 classifiers eligible
           INFO: epmt_outliers: outlier detection will be performed using 1 univariate and 0 multivariate classifi
        ers
           INFO: epmt_outliers: request to do PCA (pca=2). Input features: ['PERF_COUNT_SW_CPU_CLOCK', 'cancelled_write_bytes', 'cpu_time', 'delayacct_blkio_time', 'duration', 'exitcode', 'guest_time', 'inblock', 'invol_ctxsw', 'majflt', 'minflt', 'num_procs', 'num_threads', 'outblock', 'processor', 'rchar', 'rdtsc_duration', 'read_bytes', 'rssmax', 'syscr', 'syscw', 'systemtime', 'time_oncpu', 'time_waiting', 'timeslices', 'usertime', 'vol_ctxsw', 'wchar', 'write_bytes']
           INFO: epmt_outliers: 2 PCA components obtained: ['pca_01', 'pca_02']
           INFO: epmt_outliers: PCA variances: [0.70431608 0.16781148] (sum=0.8721275632391069)
           INFO: epmt_outliers: adjusting the PCA scores based on PCA variances
    >>> x[0]
            jobid  pca_weighted  pca_01  pca_02
        0  625151           4.2       1       0
        1  627907           1.0       0       1
        2  629322           1.0       0       1
        3  633114           0.0       0       0
        4  675992           1.0       0       1
        5  680163           0.0       0       0
        6  685001           0.0       0       0
        7  691209           0.0       0       0
        8  693129           0.0       0       0



    # Now, lets do a multimode outlier detection (multimode here means
    # using multiple univariate classifiers)
    >>> (outliers, parts) = eod.detect_outlier_jobs(['kern-6656-20190614-190245', 'kern-6656-20190614-191138', 'kern-6656-20190614-192044-outlier', 'kern-6656-20190614-194024'], methods = [es.iqr, es.modified_z_score])
   INFO: epmt_outliers: outlier detection provided 2 classifiers
   INFO: epmt_outliers: 2 classifiers eligible
   INFO: epmt_outliers: outlier detection will be performed using 2 univariate and 0 multivariate classifiers
   >>> outliers
                                      jobid  cpu_time  duration  num_procs
       0          kern-6656-20190614-190245         0         0          0
       1  kern-6656-20190614-192044-outlier         2         2          0
       2          kern-6656-20190614-194024         0         0          0
       3          kern-6656-20190614-191138         0         0          0

   >>> parts
       {'cpu_time': ({'kern-6656-20190614-190245',
          'kern-6656-20190614-191138',
          'kern-6656-20190614-194024'},
         {'kern-6656-20190614-192044-outlier'}),
        'duration': ({'kern-6656-20190614-190245',
          'kern-6656-20190614-191138',
          'kern-6656-20190614-194024'},
         {'kern-6656-20190614-192044-outlier'}),
        'num_procs': ({'kern-6656-20190614-190245',
          'kern-6656-20190614-191138',
          'kern-6656-20190614-192044-outlier',
          'kern-6656-20190614-194024'},
         set())}


    # TODO: Provide examples with multivariate classifiers

    """
    eq._empty_collection_check(jobs)
    if sanity_check:
        eq._warn_incomparable_jobs(jobs)

    # if we don't have a dataframe, get one
    if type(jobs) != pd.DataFrame:
        jobs = eq.conv_jobs(jobs, fmt='pandas')

    # check if any columns contain nans
    nan_columns = jobs.columns[jobs.isnull().any()].tolist()
    if nan_columns:
        raise ValueError('dataframe columns ({}) contain atlleast one NaN each'.format(nan_columns))

    model_params = {}
    if trained_model:
        logger.debug('using a trained model for detecting outliers')
        if type(trained_model) == int:
            trained_model = orm_get(ReferenceModel, trained_model)
        if not eq.refmodel_is_enabled(trained_model.id):
            raise RuntimeError("Trained model is disabled. You will need to enable it using 'refmodel_set_status' and try again")
        if trained_model.info_dict and trained_model.info_dict.get('pca', {}):
            logger.debug('trained model used PCA')
            if not pca:
                logger.warning('Auto-enabling PCA prior to outlier detection. In future, please call detect_outlier_jobs with pca=True when using PCA-based trained models for outlier detection')
                pca = True
    else:
        _err_col_len(jobs, 4, 'Too few jobs to do outlier detection. Need at least 4!')

    # get model parameters if available in trained model
    # skip over methods that do not exist in trained model
    methods = methods or uvod_classifiers()
    _methods = []
    logger.info('outlier detection provided {} classifiers'.format(len(methods)))
    for m in methods:
        c_name = get_classifier_name(m)
        if trained_model:
             if not c_name in trained_model.computed:
                 logger.warning("Skipping classifier {} -- could not find it in trained model".format(c_name))
                 continue
             model_params[m] = trained_model.computed[c_name]
        else:
             model_params[m] = {}
        _methods.append(m)
    methods = _methods
    logger.info('{} classifiers eligible'.format(len(methods)))
    if not methods:
        logger.error('No eligible classifiers available')
        return False

    (uv_methods, mv_methods) = partition_classifiers_uv_mv(methods)
    if uv_methods and mv_methods:
        err_msg = 'OD using both UV and MV classifiers together is unsupported'
        logger.error(err_msg)
        raise ValueError(err_msg)

    if mv_methods and (trained_model is None):
        err_msg = 'Multivariate classifiers require a trained model for outlier detection'
        logger.error(err_msg)
        raise ValueError(err_msg)

    if mv_methods and pca:
        err_msg = 'Multivariate classifiers use with PCA is neither advisable nor supported'
        logger.error(err_msg)
        raise ValueError(err_msg)

    logger.info('outlier detection will be performed using {} univariate and {} multivariate classifiers'.format(len(uv_methods), len(mv_methods)))

    # sanitize features list
    if pca and features and (features != '*'):
        logger.warning('It is strongly recommended to set features=[] when doing PCA')
    features = sanitize_features(features, jobs, trained_model)

    if pca is not False:
        logger.info("request to do PCA (pca={}). Input features: {}".format(pca, features))
        if len(features) < 5:
            logger.warning('Too few input features for PCA. Are you sure you did not want to set features=[] to enable selecting all available features?')
        if trained_model:
            # for PCA analysis if we use a trained model, then we need to
            # include the trained model jobs prior to PCA (as the scaling
            # done as part of PCA will need those jobs
            trained_model_jobs = [j.jobid for j in trained_model.jobs]
            added_model_jobs = []
            jobids_set = set(list(jobs['jobid'].values))
            if len(jobids_set - set(trained_model_jobs)) > 1:
                logger.warning('When using a trained-model+PCA, it is recommended that you do outlier detection on a single job at a time for best results')
            for mjob in trained_model.jobs:
                if mjob.jobid not in jobids_set:
                    added_model_jobs.append(mjob.jobid)
            if added_model_jobs:
                logger.debug('appending model jobs {} prior to PCA'.format(added_model_jobs))
                added_model_jobs_df = eq.get_jobs(added_model_jobs, fmt='pandas')[['jobid']+features]
                jobs = pd.concat([jobs[['jobid']+features], added_model_jobs_df], axis=0, ignore_index=True)
        (jobs_pca_df, pca_variances, pca_features, _) = pca_feature_combine(jobs, features, desired = 0.85 if pca is True else pca)

        # remove the rows of the appended model jobs
        # if trained_model and added_model_jobs:
        #     jobs_pca_df = jobs_pca_df[~jobs_pca_df.jobid.isin(added_model_jobs)].reset_index(drop=True)

        logger.info('{} PCA components obtained: {}'.format(len(pca_features), pca_features))
        logger.info('PCA variances: {} (sum={})'.format(pca_variances, np.sum(pca_variances)))
        jobs = jobs_pca_df
        features = pca_features

    # list of stuff to return from this fn
    retlist = []

    logger.debug('doing outlier detection on:\n{}'.format(jobs[['jobid'] + features]))
    # unfortunately we cannot leverage the same code for
    # univariate and multivariate classifiers, since the 
    # univariate code needs to iterate over the features
    # while the multivariate code takes them in one go
    if uv_methods:
        # initialize a df with all values set to False
        logger.debug('OD using UV classifiers: {}'.format([ m.__name__ for m in uv_methods]))
        retval = pd.DataFrame(0, columns=features, index=jobs.index)
        for c in features:
            # print('data-type for feature column {0} is {1}'.format(c, jobs[c].dtype))
            for m in uv_methods:
                m_name = get_classifier_name(m)
                # We ignore params for PCA, as the underlying PCA vector is not stable
                params = model_params[m].get(c, ()) if not pca else ()
                if params:
                    logger.debug('params[{0}][{1}]: {2}'.format(m_name, c, params))
                scores = m(jobs[c], params)[0]
                logger.debug('scores: {}'.format(scores))
                if pca and trained_model:
                    # when using PCA with trained model, we need to figure the threshold
                    # from the rows comprising of the model jobs
                    model_indices = jobs[jobs.jobid.isin(trained_model_jobs)].index.values
                    logger.debug('trained model job indices: {}'.format(list(model_indices)))
                    trained_model_scores = np.asarray(scores).take(model_indices)
                    threshold = trained_model_scores.max()
                    logger.debug('trained model scores: {}, max: {}'.format(trained_model_scores, threshold))
                else:
                    # use the max score in the refmodel if we have a trained model
                    # otherwise use the default threshold for the method
                    # For some methods like es.iqr we purposely don't
                    # have thresholds, instead those methods return a mask.
                    # So for such methods that return a mask we use a threshold of 0
                    threshold = params[0] if params else thresholds.get(m_name, 0)
                logger.debug('threshold: {}'.format(threshold))
                outlier_rows = np.where(np.abs(scores) > threshold)[0]
                logger.debug('outliers for [{}][{}] -> {}'.format(m_name,c,outlier_rows))
                retval.loc[outlier_rows,c] += 1

        # add a jobid column to the output dataframe
        retval['jobid'] = jobs['jobid']
        retval = retval[['jobid']+features]
        # now let's create a dictionary where the key is the feature
        # and he value is a tuple like ([ref_jobs],[outlier_jobs])
        parts = {}
        for f in features:
            df_ref = retval[retval[f] == 0]
            df_outl= retval[retval[f] > 0]
            parts[f] = (set(df_ref['jobid'].values), (set(df_outl['jobid'].values)))
        retlist.append(retval)
        retlist.append(parts)

    if mv_methods:
        logger.debug('OD using UV classifiers: {}'.format(mv_methods))
        # initialize a df with all values set to False
        features_str = ",".join(sorted(features))
        mvod_outliers = None
        classfiers_od_dict = {} # will store outlier vectors index by classifier
        for m in mv_methods:
            m_name = get_classifier_name(m)
            if not features_str in model_params[m]:
                logger.warning('Skipping classifier {}, as could not find model threshold for the feature set'.format(m_name))
                continue
            (model_score, model_inp) = model_params[m].get(features_str)
            model_ndarray = np.asarray(model_inp)
            logger.info('classifier {0} model threshold: {1}'.format(m_name, model_score))
            outliers_vec = mvod_scores_using_model(jobs[features].to_numpy(), model_ndarray, m, model_score)
            if outliers_vec is False:
                logger.warning('Could not score using {}, skipping it'.format(m_name))
                continue
            logger.info('outliers vector using {0}: {1}'.format(m_name, outliers_vec))
            classfiers_od_dict[m_name] = list(outliers_vec)
            # sum the bitmap vectors - the value for the ith row in the result
            # shows the number of mvod classifiers that considered the row (job) to
            # be an outlier
            mvod_outliers = outliers_vec if (mvod_outliers is None) else mvod_outliers + outliers_vec 
        mvod_df = pd.DataFrame(mvod_outliers, columns=['outlier'], index=jobs.index)
        # add a jobid column to the output dataframe
        mvod_df['jobid'] = jobs['jobid']
        mvod_df = mvod_df[['jobid','outlier']]
        mvod_df.name = ",".join([get_classifier_name(m) for m in mv_methods])
        mvod_df.name += " (" + features_str + ")"
        logger.info(mvod_df.name)
        logger.info(mvod_df)
        retlist.append(mvod_df)
        if (len(mv_methods) > 1):
            retlist.append(classfiers_od_dict)

    if pca:
        logger.info('adjusting the PCA scores based on PCA variances')
        _new_retlist = []
        for arg in retlist:
            if type(arg) == pd.DataFrame:
                if trained_model and added_model_jobs:
                    # remove model rows that we added
                    arg = retval[~arg.jobid.isin(added_model_jobs)].reset_index(drop=True)
                adjusted_df = _pca_weighted_score(arg, pca_features, pca_variances)[0]
                _new_retlist.append(adjusted_df)
            else:
                _new_retlist.append(arg)
        retlist = _new_retlist

    # return a list if we have more than one item
    # Essentially, for UV classifiers, we will return a list
    # while for MV classifiers, we will return a single dataframe
    return (retlist if len(retlist) > 1 else retlist[0])

 
# This function can be very expensive. So, we only use a single outlier
# scoring method by default. Using 2 more really takes too long.
@db_session
def detect_outlier_ops(jobs, tags=[], trained_model=None, features = FEATURES, methods=[modified_z_score], thresholds=thresholds, sanity_check=True, pca = False):
    """
    Detects outlier operations::Outlier Detection

    This function detects outlier *operations* on a set of jobs.
    You should be using this function only if you want to figure out
    which operations are outlier. If you only want to figure out the
    jobs that were outliers, it is recommended you use `detect_outlier_jobs`,
    since that runs considerably faster than `detect_outlier_ops`.

    Parameters
    ----------
          jobs : list of strings or list of objects or ORM query or dataframe
                 You need a minimum of 4 jobs without a trained model for
                 outlier detection

          tags : list of strings or list of dicts or string, optional
                 The tags define the operations which will be partitioned.
                 If not specified the unique process tags across all jobs
                 will be used

 trained_model : int, optional
                 The ID of a reference model. If not specified,
                 outlier detection will be done from within the jobs

    features   : list of strings or '*', optional
                 List of features to use for outlier detection. 
                 An empty list or '*' means use all available features.
                 Defaults to a list specified in settings

       methods : list of callables, optional 
                 This is an advanced option to specify the function(s) to use
                 for outlier detection. If unspecified it will default to
                 all the available univariate classifiers
                 If multivariate classifiers are specified, a trained model 
                 *must* be specified. We only support pyod classifiers at present 
                 for multivariate classifiers. Do not mix univariate and 
                 multivariate classifiers

    thresholds : dict, optional
                 Defines the thresholds for different classifiers.
                 This is used from settings, and ordinarily you should
                 not have to manually use this option

           pca : boolean or int or float, optional
                 False by default. If enabled, the PCA analysis will be done
                 on the features prior to outlier detection. Rather than setting
                 this option to True, you may also set this option to something
                 like: pca = 2, in which case it will mean you want two components
                 in the PCA. Or something like, pca = 0.95, which will be 
                 intepreted as meaning do PCA and automatically select the number
                 components to arrive at the number of components in the PCA.
                 If set to True, a 0.85 variance ratio will be set to enable
                 automatic selection of PCA components.
                 When pca is enabled, then the return value is a single dataframe
                 with no special ordering of rows other than they are grouped
                 by tag
    
    Returns
    -------

       When given UV classifiers: (df, dict_of_partitions, scores_df, sorted_tags, sorted_features)
       When given MV classifiers: df

    where:
       df is the dataframe that is sorted by decreasing tag importance, and
       has a bitmask showing whether a particular operation of a job was an
       outlier when contrasted with the same operation in other jobs. The 
       columns of 'df' are sorted in decreasing order of feature importance
       from left to right.
    
       The dict_of_partitions is indexed by the tag, and the value 
       is a tuple, consisting of the (<ref_part>,<outlier_part>) for the tag.
    
    scores_df is a dataframe containing the max scores for each tag against
    a particular feature. It's sorted in decreasing order of tag scores, where
    a tag_score is defined as the max of scores across all features for the tag.
    
    sorted_tags is just a sorted list of tags by decreasing tag_score
    
    sorted_features is a sorted list of features by feature_score, where
    feature_score is defined as the sum of scores for a feature across 
    all tags:

    Notes
    -----
    You cannot mix UV and MV classifiers.
    When pca is enabled, then the return value is a single dataframe
    with no special ordering of rows other than they are grouped by tag.
    
    Examples
    --------
    
    The following examples cover OD using univariate classifiers:
    jobs = [u'625151', u'627907', u'629322', u'633114', u'675992', u'680163', u'685001', u'691209', u'693129', u'696110', u'802938', u'804266']
    
    
    >>> (df, parts, scores_df, sorted_tags, sorted_features) = eod.detect_outlier_ops(jobs, methods=[es.modified_z_score])
    
    >>> df.head()
        jobid                                               tags  duration  \
    0  627907  {u'op_instance': u'13', u'op_sequence': u'69',...         0   
    1  629322  {u'op_instance': u'13', u'op_sequence': u'69',...         0   
    2  633114  {u'op_instance': u'13', u'op_sequence': u'69',...         0   
    3  675992  {u'op_instance': u'13', u'op_sequence': u'69',...         0   
    4  680163  {u'op_instance': u'13', u'op_sequence': u'69',...         0   
    
       cpu_time  num_procs  
    0         0          0  
    1         1          0  
    2         0          0  
    3         1          0  
    4         1          0  
    
    >>> scores_df.head()[['tags','duration','cpu_time']]
                                                    tags  duration  cpu_time
    0  {"op": "mv", "op_instance": "13", "op_sequence...    11.530  4043.151
    1  {"op": "mv", "op_instance": "10", "op_sequence...  1621.426     1.547
    2  {"op": "hsmget", "op_instance": "6", "op_seque...   824.428     0.973
    3  {"op": "hsmget", "op_instance": "7", "op_seque...   393.765     1.160
    4  {"op": "hsmget", "op_instance": "6", "op_seque...   387.099     0.000
    
    >>> sorted_tags[:3]
    [{u'op_instance': u'13', u'op_sequence': u'69', u'op': u'mv'}, {u'op_instance': u'10', u'op_sequence': u'60', u'op': u'mv'}, {u'op_instance': u'6', u'op_sequence': u'21', u'op': u'hsmget'}]
    
    >>> sorted_features
    ['duration', 'cpu_time', 'num_procs']

    # Now let's do one with PCA:

    >>> out_df = eod.detect_outlier_ops(['kern-6656-20190614-190245', 'kern-6656-20190614-191138', 'kern-6656-20190614-192044-outlier', 'kern-6656-20190614-194024'], features=[], pca = True, methods=[es.modified_z_score])
   INFO: epmt_outliers: request to do PCA (pca=True). Input features: ['PERF_COUNT_SW_CPU_CLOCK', 'cancelled_write_byte
s', 'cpu_time', 'delayacct_blkio_time', 'duration', 'guest_time', 'inblock', 'invol_ctxsw', 'majflt', 'minflt', 'num_pr
ocs', 'numtids', 'outblock', 'processor', 'rchar', 'rdtsc_duration', 'read_bytes', 'rssmax', 'syscr', 'syscw', 'systemt
ime', 'time_oncpu', 'time_waiting', 'timeslices', 'usertime', 'vol_ctxsw', 'wchar', 'write_bytes']
   INFO: epmt_outliers: 2 PCA components obtained: ['pca_01', 'pca_02']
   INFO: epmt_outliers: PCA variances: [0.66848523 0.24011409] (sum=0.9085993214405101)
   INFO: epmt_outliers: adjusting the PCA scores based on PCA variances

    # pick out the outlier rows
    >>> out_df[out_df.pca_weighted > 0]
                                jobid                                               tags  pca_weighted  pca_01  pca_02
2   kern-6656-20190614-192044-outlier  {'op': 'build', 'op_instance': '4', 'op_sequen...           3.8       1       1
6   kern-6656-20190614-192044-outlier  {'op': 'clean', 'op_instance': '5', 'op_sequen...           3.8       1       1
10  kern-6656-20190614-192044-outlier  {'op': 'configure', 'op_instance': '3', 'op_se...           3.8       1       1
14  kern-6656-20190614-192044-outlier  {'op': 'download', 'op_instance': '1', 'op_seq...           3.8       1       1
18  kern-6656-20190614-192044-outlier  {'op': 'extract', 'op_instance': '2', 'op_sequ...           3.8       1       1

    # The example below is for MVOD+trained model
    >>> r = eq.create_refmodel(['kern-6656-20190614-190245', 'kern-6656-20190614-191138', 'kern-6656-20190614-194024'], op_tags='*', outlier_methods = es.mvod_classifiers())
    >>> jobs = ['kern-6656-20190614-190245', 'kern-6656-20190614-191138', 'kern-6656-20190614-192044-outlier', 'kern-6656-20190614-194024']
    >>> df, part = eod.detect_outlier_ops(jobs, methods = es.mvod_classifiers(), trained_model = r['id'])
    >>> df
                                    jobid                                               tags  outlier
    0           kern-6656-20190614-190245  {'op': 'build', 'op_instance': '4', 'op_sequen...        0
    1           kern-6656-20190614-191138  {'op': 'build', 'op_instance': '4', 'op_sequen...        0
    2   kern-6656-20190614-192044-outlier  {'op': 'build', 'op_instance': '4', 'op_sequen...        3
    3           kern-6656-20190614-194024  {'op': 'build', 'op_instance': '4', 'op_sequen...        0
    4           kern-6656-20190614-190245  {'op': 'clean', 'op_instance': '5', 'op_sequen...        0
    5           kern-6656-20190614-191138  {'op': 'clean', 'op_instance': '5', 'op_sequen...        0
    6   kern-6656-20190614-192044-outlier  {'op': 'clean', 'op_instance': '5', 'op_sequen...        3
    7           kern-6656-20190614-194024  {'op': 'clean', 'op_instance': '5', 'op_sequen...        0
    8           kern-6656-20190614-190245  {'op': 'configure', 'op_instance': '3', 'op_se...        0
    9           kern-6656-20190614-191138  {'op': 'configure', 'op_instance': '3', 'op_se...        0
    10  kern-6656-20190614-192044-outlier  {'op': 'configure', 'op_instance': '3', 'op_se...        3
    11          kern-6656-20190614-194024  {'op': 'configure', 'op_instance': '3', 'op_se...        0
    12          kern-6656-20190614-190245  {'op': 'download', 'op_instance': '1', 'op_seq...        0
    13          kern-6656-20190614-191138  {'op': 'download', 'op_instance': '1', 'op_seq...        0
    14  kern-6656-20190614-192044-outlier  {'op': 'download', 'op_instance': '1', 'op_seq...        3
    15          kern-6656-20190614-194024  {'op': 'download', 'op_instance': '1', 'op_seq...        0
    16          kern-6656-20190614-190245  {'op': 'extract', 'op_instance': '2', 'op_sequ...        0
    17          kern-6656-20190614-191138  {'op': 'extract', 'op_instance': '2', 'op_sequ...        0
    18  kern-6656-20190614-192044-outlier  {'op': 'extract', 'op_instance': '2', 'op_sequ...        3
    19          kern-6656-20190614-194024  {'op': 'extract', 'op_instance': '2', 'op_sequ...        0

    >>> part
    {'{"op": "build", "op_instance": "4", "op_sequence": "4"}': {'pyod.models.cof': [0, 0, 1, 0], 'pyod.models.hbos': [0, 0, 1, 0], 'pyod.models.mcd': [0, 0, 1, 0], 'pyod.models.ocsvm': [0, 0, 0, 0]}, '{"op": "clean", "op_instance": "5", "op_sequence": "5"}': {'pyod.models.cof': [0, 0, 1, 0], 'pyod.models.hbos': [0, 0, 1, 0], 'pyod.models.mcd': [0, 0, 1, 0], 'pyod.models.ocsvm': [0, 0, 0, 0]}, '{"op": "configure", "op_instance": "3", "op_sequence": "3"}': {'pyod.models.cof': [0, 0, 1, 0], 'pyod.models.hbos': [0, 0, 1, 0], 'pyod.models.mcd': [0, 0, 1, 0], 'pyod.models.ocsvm': [0, 0, 0, 0]}, '{"op": "download", "op_instance": "1", "op_sequence": "1"}': {'pyod.models.cof': [0, 0, 1, 0], 'pyod.models.hbos': [0, 0, 1, 0], 'pyod.models.mcd': [0, 0, 1, 0], 'pyod.models.ocsvm': [0, 0, 0, 0]}, '{"op": "extract", "op_instance": "2", "op_sequence": "2"}': {'pyod.models.cof': [0, 0, 1, 0], 'pyod.models.hbos': [0, 0, 1, 0], 'pyod.models.mcd': [0, 0, 1, 0], 'pyod.models.ocsvm': [0, 0, 0, 0]}}
    

    """
    eq._empty_collection_check(jobs)
    if sanity_check:
        eq._warn_incomparable_jobs(jobs)
    jobids = eq.get_jobs(jobs, fmt='terse')


    tags = tags_list(tags)
    jobs_tags_set = set()
    unique_job_tags = eq.job_proc_tags(jobs, fold=False)
    for t in unique_job_tags:
        jobs_tags_set.add(dumps(t, sort_keys=True))

    model_params = {}
    if trained_model:
        model_tags_set = set()
        logger.debug('using a trained model for detecting outliers')
        if type(trained_model) == int:
            trained_model = orm_get(ReferenceModel, trained_model)
        if not eq.refmodel_is_enabled(trained_model.id):
            raise RuntimeError("Trained model is disabled. You will need to enable it using 'refmodel_set_enabled' and try again")
        #logger.debug('Ref. model scores: {0}'.format(trained_model.computed))
        #logger.debug('Ref. model op_tags: {0}'.format(trained_model.op_tags))
        logger.debug('Ref model contains {0} op_tags'.format(len(trained_model.op_tags)))
        for t in trained_model.op_tags:
            model_tags_set.add(dumps(t, sort_keys=True))
        if not tags:
            tags = trained_model.op_tags
        if jobs_tags_set != model_tags_set:
            logger.warning('Set of unique tags are different from the model')
            if (jobs_tags_set - model_tags_set):
                logger.warning('Jobs have the following tags, not found in the model: {0}'.format(jobs_tags_set - model_tags_set))
            if (model_tags_set - jobs_tags_set):
                logger.warning('Model has the following tags, not found in the jobs: {0}'.format(model_tags_set - jobs_tags_set))
    else:
        _err_col_len(jobs, 4, 'Too few jobs to do outlier detection. Need at least 4!')
    if not tags:
        tags = unique_job_tags

    # if we have a trained model then we can only use the subset
    # of 'tags' that is found in the trained model
    tags_to_use = []
    if trained_model:
        if tags == trained_model.op_tags:
            tags_to_use = tags
        else:
            for d in trained_model.op_tags:
                if (dict_in_list(d, tags)):
                    tags_to_use.append(d)
    else:
        tags_to_use = tags
 
    methods = methods or uvod_classifiers()
    _methods = set() 
    for t in tags_to_use:
        t = dumps(t, sort_keys=True)
        model_params[t] = {}
        for m in methods:
            m_name = get_classifier_name(m)
            model_params[t][m] = {}
            if trained_model:
                if m_name in trained_model.computed[t]:
                    model_params[t][m] = trained_model.computed[t][m_name]
                    _methods.add(m)
            else:
                _methods.add(m)
    methods = list(_methods)
    logger.info('{} classifiers eligible'.format(len(methods)))
    if not methods:
        logger.error('No eligible classifiers available')
        return False

    (uv_methods, mv_methods) = partition_classifiers_uv_mv(methods)

    if uv_methods and mv_methods:
        err_msg = 'OD using both UV and MV classifiers together is unsupported'
        logger.error(err_msg)
        raise ValueError(err_msg)

    if mv_methods:
        if (trained_model is None):
            err_msg = 'Multivariate classifiers require a trained model for outlier detection'
            logger.error(err_msg)
            raise ValueError(err_msg)
        if pca:
            err_msg = 'Multivariate classifiers use with PCA is neither advisable nor supported'
            logger.error(err_msg)
            raise ValueError(err_msg)

    if trained_model and pca:
        # for PCA analysis if we use a trained model, then we need to
        # include the trained model jobs prior to PCA (as the scaling
        # done as part of PCA will need those jobs
        trained_model_jobs = [j.jobid for j in trained_model.jobs]
        added_model_jobs = []
        jobids_set = set(jobids)
        if len(jobids_set - set(trained_model_jobs)) > 1:
            logger.warning('When using a trained-model+PCA, it is recommended that you do outlier detection on a single job at a time for best results')
        for mjob in trained_model.jobs:
            if mjob.jobid not in jobids_set:
                added_model_jobs.append(mjob.jobid)
        if added_model_jobs:
            logger.debug('appending model jobs {} prior to PCA'.format(added_model_jobs))
            jobs = jobids + added_model_jobs

    # get the dataframe of aggregate metrics, where each row
    # is an aggregate across a group of processes with a particular
    # jobid and tag
    ops = eq.get_op_metrics(jobs=jobs, tags=tags_to_use)
    if len(ops) == 0:
        logger.warning('no matching tags found in the tag set: {0}'.format(tags_to_use))
        return (None, {})
    if pca and features and (features != '*'):
        logger.warning('It is strongly recommended to set features=[] when doing PCA')
    features = sanitize_features(features, ops, trained_model)

    if pca:
        logger.info("request to do PCA (pca={}). Input features: {}".format(pca, features))
        if len(features) < 5:
            logger.warning('Too few input features for PCA. Are you sure you did not want to set features=[] to enable selecting all available features?')
        logger.debug('jobid,tags:\n{}'.format(ops[['jobid','tags']]))
        (ops_pca_df, pca_variances, pca_features, _) = pca_feature_combine(ops, features, desired = 0.85 if pca is True else pca)

        logger.info('{} PCA components obtained: {}'.format(len(pca_features), pca_features))
        logger.info('PCA variances: {} (sum={})'.format(pca_variances, np.sum(pca_variances)))
        ops = ops_pca_df
        features = pca_features

    logger.debug('jobid,tags:\n{}'.format(ops[['jobid', 'tags']]))
    if uv_methods:
        logger.debug('OD using UV classifiers: {}'.format(uv_methods))
        retval = pd.DataFrame(0, columns=features, index=ops.index)

        # the dict below will be indexed by tag, and will store
        # the sum of the max value of scores for each feature, where the
        # the sum is done across 'methods'. So, if we have two methods:
        # z_score, and modified_z_score, and for a particular feature,
        # say 'duration', the max z_score for tag -- op_seq:45 -- is
        # 1.5 and 1.0. Then the sum is 2.5. And now suppose we have
        # three features: duration, cpu_time, num_procs, with
        # the sums being [2.5, 3.5, 1.0], then, we would have:
        # { 'op_seq:45': [2.5, 3.5, 1.0], ... }
        # So, the ordering of elements in the list is in the order of the
        # features.
        #
        tags_max = {}
        # now we iterate over tags and for each tag we select
        # the rows from the ops dataframe that have the same tag;
        # the select rows will have different job ids
        for tag in tags_to_use:
            t = dumps(tag, sort_keys=True)
            # select only those rows with matching tag
            rows = ops[ops.tags == tag] # pylint: disable=no-member
            logger.debug('Processing tag: {}, rows index: {}'.format(tag, rows.index.values))
            logger.debug('\n:{}'.format(rows[['jobid', 'tags']]))
            # logger.debug('input: \n{0}\n'.format(rows[['tags']+features]))
            tags_max[t] = []
            for c in features:
                score_diff = 0
                for m in methods:
                    # We ignore params for PCA, as the underlying PCA vector is not stable
                    params = model_params[t][m].get(c, ()) if not pca else ()
                    m_name = get_classifier_name(m)
                    logger.debug(rows[c])
                    scores = m(rows[c], params)[0]
                    logger.debug('scores: {}'.format(scores))
                    if pca and trained_model:
                        # when using PCA with trained model, we need to figure the threshold
                        # from the rows comprising of the model jobs
                        _r = rows.reset_index(drop=True)
                        model_indices = _r[_r.jobid.isin(trained_model_jobs)].index.values
                        logger.debug('trained model job indices: {}'.format(list(model_indices)))
                        trained_model_scores = np.asarray(scores).take(model_indices)
                        threshold = trained_model_scores.max()
                        logger.debug('trained model scores: {}, max: {}'.format(trained_model_scores, threshold))
                    else:
                        # use the max score in the refmodel if we have a trained model
                        # otherwise use the default threshold for the method
                        threshold = params[0] if params else thresholds.get(m_name, 0)
                    logger.debug('threshold: {}'.format(threshold))
                    outlier_rows = np.where(np.abs(scores) > threshold)[0]
                    score_diff += max(max(scores) - threshold, 0)
                    # map to the outlier rows indices to the indices in the original df
                    outlier_rows = rows.index[outlier_rows].values
                    logger.debug('outliers for [{}][{}][{}] -> {}'.format(t,m_name,c, outlier_rows))
                    retval.loc[outlier_rows,c] += 1
                tags_max[t].append(round(score_diff, 3))
        retval['jobid'] = ops['job']
        retval['tags'] = ops['tags']
        retval = retval[['jobid', 'tags']+features]

        if pca:
            if trained_model and added_model_jobs:
                # remove model rows that we added
                retval = retval[~retval.jobid.isin(added_model_jobs)].reset_index(drop=True)
            logger.info('adjusting the PCA scores based on PCA variances')
            adjusted_df = _pca_weighted_score(retval, pca_features, pca_variances, 2)[0]
            return adjusted_df

        # now lets sort the tags by the max of the scores across the features
        sorted_tags_with_scores = sorted(tags_max.items(), key=lambda e: max(e[1]), reverse=True)
        sorted_tags = [loads(x[0]) for x in sorted_tags_with_scores]

        _trows = []
        for e in sorted_tags_with_scores:
            _trows.append([e[0]] + list(e[1]))
        # the dataframe below has the scores for the tags by feature,
        # and it's sorted in order of desc tag importance
        tag_scores_df = pd.DataFrame(_trows, columns=['tags']+features)

        # now let's figure out the sorted feature list by summing the 
        # scores for the feature across tags
        f_scores = []
        for f in features:
            f_scores.append((f, tag_scores_df[f].sum()))
        sorted_f_scores = sorted(f_scores, key=lambda e: e[1], reverse=True)
        sorted_features = [x[0] for x in  sorted_f_scores]

        # now let's create an output data from of outliers using the ordering
        # of tags in sorted_tags
        all_rows = []
        for t in sorted_tags:
            all_rows.append(retval[retval.tags == t])
        sorted_df = pd.concat(all_rows, ignore_index=True)
            
        # partition using tags
        parts = {}
        for tag in tags_to_use:
            dft = retval[retval.tags == tag]
            q_ref = "&".join(["{0} == 0".format(f) for f in features])
            dft_ref = dft.query(q_ref).reset_index(drop=True)
            q_outlier = "|".join(["{0} > 0".format(f) for f in features])
            dft_outlier = dft.query(q_outlier).reset_index(drop=True)
            parts[dumps(tag)] = (set(dft_ref['jobid'].values), (set(dft_outlier['jobid'].values)))

        # order the columns in the dataframe by decreasing feature importance (left to right)
        final_df = sorted_df[['jobid', 'tags']+sorted_features]
        final_scores_df = tag_scores_df[['tags']+sorted_features]
        return (final_df, parts, final_scores_df, sorted_tags, sorted_features)
    else:
        # MVOD
        logger.debug('OD using UV classifiers: {}'.format(mv_methods))
        # initialize a df with all values set to False
        features_str = ",".join(sorted(features))
        classfiers_od_dict = {} # will store outlier vectors indexed by tag and then by classifier
        mvod_df = pd.DataFrame(0, columns=['outlier'], index=ops.index)
        for tag in tags_to_use:
            mvod_outliers = None
            t = dumps(tag, sort_keys=True)
            classfiers_od_dict[t] = {}
            # select only those rows with matching tag
            rows = ops[ops.tags == tag] # pylint: disable=no-member
            logger.debug('Processing tag: {}, rows index: {}'.format(tag, rows.index.values))
            logger.debug('\n:{}'.format(rows[['jobid', 'tags']]))
            for m in mv_methods:
                m_name = get_classifier_name(m)
                if not features_str in model_params[t][m]:
                    logger.warning('Skipping classifier {}, as could not find model threshold for the feature set for tag {}'.format(m_name, t))
                    continue
                (model_score, model_inp) = model_params[t][m].get(features_str)
                model_ndarray = np.asarray(model_inp)
                logger.debug('classifier {} model threshold for tag [{}]: {}'.format(m_name, t, model_score))
                outliers_vec = mvod_scores_using_model(rows[features].to_numpy(), model_ndarray, m, model_score)
                if outliers_vec is False:
                     logger.warning('Could not score using {}, skipping it'.format(m_name))
                     continue
                logger.debug('outliers vector using {} for tag [{}]: {}'.format(m_name, t, outliers_vec))
                classfiers_od_dict[t][m_name] = list(outliers_vec)
                # sum the bitmap vectors - the value for the ith row in the result
                # shows the number of mvod classifiers that considered the row (job) to
                # be an outlier
                mvod_outliers = outliers_vec if (mvod_outliers is None) else mvod_outliers + outliers_vec 
            logger.info('Outlier vector for tag [{}]: {}'.format(t, mvod_outliers))
            outlier_indices = np.where(mvod_outliers > 0)[0]
            # map to the outlier rows indices to the indices in the original df
            outlier_rows = rows.index[outlier_indices].values
            logger.debug('Outlier indices (in original df) for tag [{}] -> {}'.format(t, outlier_rows))
            mvod_df.loc[outlier_rows,'outlier'] = mvod_outliers[mvod_outliers > 0]
        # add a jobid column to the output dataframe
        mvod_df['jobid'] = ops['jobid']
        mvod_df['tags'] = ops['tags']
        mvod_df = mvod_df[['jobid','tags','outlier']]
        mvod_df.name = ",".join([get_classifier_name(m) for m in mv_methods])
        mvod_df.name += " (" + features_str + ")"
        logger.info(mvod_df.name)
        logger.info(mvod_df)
        return(mvod_df, classfiers_od_dict)


def detect_outliers(df, features=[], methods=[]):
    """
    Generic function to detect outlier rows in a dataframe::Outlier Detection

    This is a generic outlier detection function. You should probably be using
    specialized ones such as detect_outlier_{jobs,ops,processes,threads}

    Parameters
    ----------
               df : dataframe
                    Input dataframe
         features : list, optional
                    List of features to use for outlier detection.
                    Defaults to all the columns in the dataframe.
          methods : list, optional
                    List of functions to use for outlier detection
                    Defaults to all available univariate classifiers
 

    Notes
    -----
    This function currently supports only univariate classifiers. Trained models 
    are not presently supported, either.
    """
    eq._empty_collection_check(df)
    features = features or list(df.columns.values)
    retval = pd.DataFrame(0, columns=features, index=df.index)
    methods = methods or uvod_classifiers()
    logger.debug("Doing outlier detection using: {}".format(features))
    logger.debug("Using the following classifiers: {}".format([f.__name__ for f in methods]))
    for c in features:
        for m in methods:
            m_name = get_classifier_name(m)
            scores = m(df[c])[0]
            logger.debug('classifier[{}], feature[{}], scores: {}'.format(m_name, c, scores))
            threshold = thresholds.get(m_name, 0)
            logger.debug('threshold: {}'.format(threshold))
            outlier_rows = np.where(np.abs(scores) > threshold)[0]
            logger.debug('outliers for [{}][{}] -> {}'.format(m_name,c,outlier_rows))
            retval.loc[outlier_rows,c] += 1
    return retval

def detect_outlier_processes(processes, features=['duration','cpu_time'], methods=[]):
    """
    This function detects outlier processes from within the input set::Outlier Detection

    Parameters
    ----------
        processes : dataframe
                    Input dataframe of processes
         features : list, optional
                    List of features to use for outlier detection.
          methods : list, optional
                    List of functions to use for outlier detection
                    Defaults to all available univariate classifiers

    Notes
    -----
    This function currently supports only univariate classifiers. Trained models 
    are not presently supported, either.
    """
    return detect_outliers(processes, features=features, methods=methods)

def detect_outlier_threads(threads, features=['usertime','systemtime', 'rssmax'], methods=[]):
    """
    This function detects outlier threads from within the input set::Outlier Detection

    Parameters
    ----------
        processes : dataframe
                    Input dataframe of threads
         features : list, optional
                    List of features to use for outlier detection.
          methods : list, optional
                    List of functions to use for outlier detection
                    Defaults to all available univariate classifiers

    Notes
    -----
    This function currently supports only univariate classifiers. Trained models 
    are not presently supported, either.
    """
    return detect_outliers(threads, features=features, methods=methods)


@db_session
def detect_rootcause(jobs, inp, features = FEATURES,  methods = [modified_z_score]):
    """
    Performs root-cause analysis on a job given a set of reference jobs::RCA

    Parameters
    ----------
          jobs : list of strings or list of objects or ORM query or int
                 jobs can be replaced with the reference ID of a trained model

           inp : string or Series or a dataframe with a single column
                 inp represents the entity that is an outlier for which
                 you want to perform RCA

    features   : list of strings or '*', optional
                 List of features to use for outlier detection. 
                 An empty list or '*' means use all available features.
                 Defaults to a list specified in settings

       methods : list of callables, optional 
                 This is an advanced option to specify the function(s) to use
                 for outlier detection. If unspecified it will default to MADZ

    Returns
    -------
        (res, df, sorted_feature_list),
    where 'res' is True on sucess and False otherwise,
    df is a dataframe that ranks the features from left to right according
    to the difference of the score for the input with the score for the reference
    for the feature. The sorted_tuples consists of a list of tuples, where each
    tuple (feature,<diff_score>)
    """
    if type(jobs) == int:
        jobs = eq.conv_jobs(orm_get(ReferenceModel, jobs).jobs, fmt='pandas')
    elif type(jobs) != pd.DataFrame:
        jobs = eq.conv_jobs(jobs, fmt='pandas')
    if type(inp) != pd.DataFrame:
        inp = eq.conv_jobs(inp, fmt='pandas')
    return rca(jobs, inp, features, methods)

@db_session
def detect_rootcause_op(jobs, inp, tag, features = FEATURES,  methods = [modified_z_score]):
    """
    Performs root-cause analysis (RCA) for an operation::RCA

    Parameters
    ----------
          jobs : list of strings or list of objects or ORM query or int
                 jobs can be replaced with the reference ID of a trained model

           inp : string or Series or a dataframe with a single column
                 inp represents the entity that is an outlier for which
                 you want to perform RCA

           tag : string or dict
                 This is used to select the operation

      features : list of strings or '*', optional
                 List of features to use for outlier detection. 
                 An empty list or '*' means use all available features.
                 Defaults to a list specified in settings

       methods : list of callables, optional 
                 This is an advanced option to specify the function(s) to use
                 for outlier detection. If unspecified it will default to MADZ
    
    Returns
    -------
        (res, df, sorted_feature_list),
    where 'res' is True on sucess and False otherwise,
    df is a dataframe that ranks the features from left to right according
    to the difference of the score for the input with the score for the reference
    for the feature. The sorted_tuples consists of a list of tuples, where each
    tuple (feature,<diff_score>)
    
    Examples
    --------
    >>> (retval, df, s) = eod.detect_rootcause_op([u'kern-6656-20190614-190245', u'kern-6656-20190614-191138', u'kern-6656-20190614-194024'], u'kern-6656-20190614-192044-outlier', tag = 'op_sequence:4', methods=[es.modified_z_score])
    
    >>> df
                                  cpu_time      duration  num_procs
    count                     3.000000e+00  3.000000e+00          3
    mean                      3.812180e+08  2.205502e+09       9549
    std                       4.060242e+05  4.762406e+07          0
    min                       3.808073e+08  2.158731e+09       9549
    25%                       3.810175e+08  2.181285e+09       9549
    50%                       3.812277e+08  2.203839e+09       9549
    75%                       3.814234e+08  2.228887e+09       9549
    max                       3.816191e+08  2.253935e+09       9549
    input                     5.407379e+08  5.014023e+09       9549
    ref_max_modified_z_score  7.246000e-01  7.491000e-01          0
    modified_z_score          2.748777e+02  4.202000e+01          0
    modified_z_score_ratio    3.793510e+02  5.609398e+01          0
    >>> s
    [('cpu_time', 379.350952249517), ('duration', 56.09397944199707), ('num_procs', 0.0)]
    """
    if not tag:
        print('You must specify a non-empty tag')
        return (False, None, None)
    if type(jobs) == int:
        jobs = eq.conv_jobs(orm_get(ReferenceModel, jobs).jobs, fmt='orm')
    jobs = eq.conv_jobs(jobs, fmt='orm')
    inp = eq.conv_jobs(inp, fmt='orm')
    if inp.count() > 1:
        print('You can only do RCA for a single "inp" job')
        return (False, None, None)
    tag = tag_from_string(tag) if (type(tag) == str) else tag
    ref_ops_df = eq.get_op_metrics(jobs, tag)
    inp_ops_df = eq.get_op_metrics(inp, tag)
    unique_tags = set([str(d) for d in ref_ops_df['tags'].values])
    if unique_tags != set([str(tag)]):
        # this is just a sanity check to make sure we only compare
        # rows that have the same tag. Ordinarily this code won't be
        # triggered as eq.get_op_metrics will only return rows that match 'tag'
        print('ref jobs have multiple distinct tags({0}) that are superset of this specified tag. Please specify an exact tag match'.format(unique_tags))
        return (False, None, None)
    return rca(ref_ops_df, inp_ops_df, features, methods)


def pca_feature_combine(inp_df, inp_features = [], desired = 2, retain_features = False):
    '''
    Perform PCA on a dataframe with multiple features::Data Reduction

    Performs PCA and returns a new dataframe containing
    the new PCA features as columns. The returned dataframe
    does not contain the old features unless retain_features
    is enabled.

    Parameters
    ----------

       inp_df : dataframe
                Input dataframe where some or all of the columns are features.

 inp_features : list of strings, optional
                A list of features to use. If not set, the feature set
                will be automatically determined

      desired : int (>= 1) or float (< 1.0), optional 
                If an integer (>= 1) it refers to the desired number of PCA 
                components. It may be set instead to a float < 1.0, in which 
                case it refers to the desired PCA variance ratio. Defaults
                to 2, meaning we want 2 PCA components

retain_features: boolean, optional 
                Defaults to False. If enabled, the input features
                will also be copied into the output dataframe.

    Returns
    -------
    (out_df, pca_variance_ratios_list, pca_feature_names, features_df)

    where:
                 out_df : Output dataframe consisting of the jobids, PCA feature
                          columns and optionally the original feature columns if
                          retain_features is set.
pca_variance_ratios_list: List of variance ratios. You should
                          sum them to ensure they capture the variance of the
                          original data (ideally 80% or higher)
       pca_feature_names: List of PCA component names
             features_df: Dataframe of shape (n_pca_components X num_features)
                          This dataframe can be used to determine the feature
                          weights used to construct the PCA components. The rows
                          correspond to the PCA components in order. So the first
                          row is the most important. You probably want to use
                          the absolute values of the values in this dataframe.

    Examples
    --------
        >>> jobs = eq.get_jobs(['625151', '627907', '629322', '633114', '675992', '680163', '685001', '691209', '693129'], fmt='pandas')
        >>> (df, variances, pca_features, features_df) = eod.pca_feature_combine(jobs)
        >>> df.iloc[:,[0,1,2,3]]
            jobid     pca_01    pca_02                                      all_proc_tags
        0  625151  11.748975 -0.700262  [{'op': 'cp', 'op_instance': '1', 'op_sequence...
        1  627907  -0.408930  1.383793  [{'op': 'cp', 'op_instance': '11', 'op_sequenc...
        2  629322  -0.485693  5.288491  [{'op': 'cp', 'op_instance': '11', 'op_sequenc...
        3  633114  -2.183437 -1.234823  [{'op': 'cp', 'op_instance': '11', 'op_sequenc...
        4  675992  -1.429851  0.082807  [{'op': 'cp', 'op_instance': '11', 'op_sequenc...
        5  680163  -1.847891 -1.319421  [{'op': 'cp', 'op_instance': '11', 'op_sequenc...
        6  685001  -2.000026 -1.283439  [{'op': 'cp', 'op_instance': '11', 'op_sequenc...
        7  691209  -1.848527 -1.166007  [{'op': 'cp', 'op_instance': '11', 'op_sequenc...
        8  693129  -1.544619 -1.051139  [{'op': 'cp', 'op_instance': '11', 'op_sequenc...

        # Ideally, we want the variances sum to be at least 80% or more to have confidence in PCA
        >>> variances
            array([0.70431608, 0.16781148])

        >>> pca_features
            ['pca_01', 'pca_02']

        # we can determine which features are important and contributed to
        # creating the pca components:
        >>> features_df
        PERF_COUNT_SW_CPU_CLOCK  cancelled_write_bytes  cpu_time  ...  vol_ctxsw     wchar  write_bytes
     0                 0.232936               0.025472  0.233724  ...   0.236599  0.235911     0.235061
     1                 0.061551              -0.444676  0.053389  ...  -0.047559 -0.059013     0.007000

        # Above, the first row corresponds to pca_01 the first pca component
        # and is therefore much more important (0.70 / 0.16 ratio) if you
        # look at the variances. And in the first row you can see which features
        # are important:

        >>> abs(features_df.loc[0]).sort_values(ascending = False)[:24]
        usertime                   0.237337
        minflt                     0.236682
        vol_ctxsw                  0.236599
        timeslices                 0.236405
        wchar                      0.235911
        syscw                      0.235876
        rchar                      0.235857
        num_threads                0.235837
        num_procs                  0.235835
        rssmax                     0.235728
        syscr                      0.235621
        time_waiting               0.235487
        outblock                   0.235061
        write_bytes                0.235061
        time_oncpu                 0.233821
        cpu_time                   0.233724
        PERF_COUNT_SW_CPU_CLOCK    0.232936
        systemtime                 0.166972
        duration                   0.137853
        rdtsc_duration             0.060931
        inblock                    0.047433
        read_bytes                 0.047433
        invol_ctxsw                0.034819
        cancelled_write_bytes      0.025472
        majflt                     8.205073e-03
        exitcode                   5.236299e-18
        delayacct_blkio_time       3.434487e-18
        guest_time                 7.059201e-19
        processor                  0.000000e+00


        As you can see all the features listed above are important and roughly
        equal in importance (except rdtsc_duration onwards). The irrelevant
        fetaures are at the bottom of the list. We only check the first PCA
        component (the first row of features_df) because the other is much
        lower in importance. On the second PCA component, we might care about
        the top few features:

        >>> abs(features_df.loc[1]).sort_values(ascending = False)[:10]
        inblock                  0.472362
        read_bytes               0.472362
        majflt                   0.465210
        cancelled_write_bytes    0.444676
        systemtime               0.234107
        rdtsc_duration           0.150492
        duration                 0.119744
        invol_ctxsw              0.073167
        syscr                    0.062168
        rssmax                   0.061841
        

        >>> x = eod.detect_outlier_jobs(df, features = pca_features)
        >>> x[0]
            jobid  pca_01  pca_02
        0  625151       1       0
        1  627907       0       1
        2  629322       0       1
        3  633114       0       0
        4  675992       0       1
        5  680163       0       0
        6  685001       0       0
        7  691209       0       0
        8  693129       0       0

        # We don't care about pca_02 if pca_01 is not set,
        # So we want to do an & operation like below:
        >>> y = x[0]
        >>> y['pca_02'] = y['pca_01'] & y['pca_02']
        >>> y
            jobid  pca_01  pca_02
        0  625151       1       0
        1  627907       0       0
        2  629322       0       0
        3  633114       0       0
        4  675992       0       0
        5  680163       0       0
        6  685001       0       0
        7  691209       0       0
        8  693129       0       0

    IOW, 625151 is an outlier according to pca_01.        
    '''

    from epmt_stat import pca_stat
    if type(inp_df) != pd.DataFrame:
        logger.error('Input needs to be a pandas dataframe')
        return False

    features = sanitize_features(inp_features, inp_df)
    logger.debug('PCA input features: {}'.format(features))
    # check if df contains nans, if so print out the columns
    nan_cols = inp_df.columns[inp_df.isnull().any()].tolist()
    if nan_cols:
        raise ValueError('PCA input dataframe contains nans in columns: {}'.format(nan_cols))
    inp_data = inp_df[features].to_numpy()
    (pca_data, pca_) = pca_stat(inp_data, desired)
    pca_feature_names = []
    features_df = pd.DataFrame(data = pca_.components_, columns=features)
    for i in range(len(pca_.explained_variance_ratio_)):
        pca_feature_names.append('pca_{:02d}'.format(i+1))
    out_df = pd.DataFrame(data = pca_data, columns = pca_feature_names, index = inp_df.index)

    inp_features_set = set(features)
    for c in inp_df.columns.values:
        # input features don't need to be in the output df 
        # unless retain_features is set
        if (not(retain_features)) and c in inp_features_set: continue
        out_df[c] = inp_df[c]
    # make sure jobid is the first column, followed by the pca columns
    # in the output dataframe
    if 'jobid' in inp_df.columns.values:
        out_cols = ['jobid'] + pca_feature_names + sorted(list(set(out_df.columns.values) - set(['jobid'] + pca_feature_names)))
        out_df = out_df[out_cols]
    return (out_df, pca_.explained_variance_ratio_, pca_feature_names, features_df)


def _pca_weighted_score(pca_df, pca_features, variances, index = 1):
    '''
    Compute a weighted PCA score using covariance ratios

    Takes an input dataframe consisting of PCA outlier scores
    and returns a dataframe comprising of an additional column
    -- 'pca_weighted' -- which is obtained by weighting the
    individual PCA feature scores by their variance weight.

    Parameters
    ----------
         pca_df : dataframe
                  Input dataframe consisting of PCA columns
   pca_features : list of strings
                  PCA feature names
      variances : tuple or list of floats
                  List or tuple of floats representing the variance ratios
                  of the PCA columns. Must be in the same order as
                  `pca_features`
          index : int, optional
                  Column number where to insert the pca_weighted column
                  in the output dataframe

    Returns
    -------
        new_df : dataframe
                 New dataframe, which is a copy of the old one with
                 an additional 'PCA_weighted' column
pca_weight_vec : The newly added PCA weighted vector

    Notes
    -----
    For example, if the input df is like:
      jobid    pca_01     pca_02
      xxxx     1          0
      yyyy     0          1
      zzzz     0          0

    And the variances are: [0.75, 0.25]

    A new column is added, by mutiplying the pca_1 column (0.75/0.25 = 3)
    and pca_2 column by (0.25/0.25 = 1) and the summing the resultant vectors
       jobid  pca_weighted   pca_01     pca_02
       xxxx     3              1          0
       yyyy     1              0          1
       zzzz     0              0          0

    The new vector is also returned as a separate element, with the
    return value being a tuple (new_df, pca_weight_vec)
    '''
    np_variances = np.asarray(variances)
    np_scale_factors = np.round(np_variances * (1/np.min(np_variances)), 2)
    pca_data = pca_df[pca_features].to_numpy()
    pca_weighted_vec = np.round(np.sum(pca_data * np_scale_factors, axis=1), 1)
    out_df = pca_df.copy()
    out_df.insert(index, 'pca_weighted', pca_weighted_vec)
    return (out_df, pca_weighted_vec)

def pca_feature_rank(jobs, inp_features = []):
    '''
    Performs 2-component PCA and feature-ranking::Data Reduction

    Parameters
    ----------
           jobs : list of strings or list of Job objects or ORM or dataframe
                  Collection of jobs
    inp_features: list of strings, optional
                  The list of features to use. If empty, all available
                  input features will be used.

    Returns
    -------
    (features_df, sorted_features), where:

        features_df is a dataframe with 3 rows. The first two rows 
        are the feature coefficients for the two PCA components 
        (the first being more important than the second). The third 
        row uses the PCA variances as weights and determines a
        composite absolute score for the feature. The dataframe columns
        are sorted from left-to-right in decreasing feature importance.

        sorted_features is a sorted list of tuples of the form:
         [(featureN, scoreN), ...]
        The list is sorted in the decreasing order of feature importance.

    Notes
    -----
    This function is just a simple wrapper around pca_feature_combine.

    Examples
    --------
    >>> df, sorted_features = pca_feature_rank(['kern-6656-20190614-190245', 'kern-6656-20190614-191138', 'kern-6656-20190614-192044-outlier', 'kern-6656-20190614-194024'])
    ...
    DEBUG: epmt_stat: PCA explained variance ratio: [0.68112048 0.24584736], sum(0.9269678411657647)
    DEBUG: epmt_outliers: normalized weights: [0.734783288753193, 0.2652167112468071]
    >>> df
         rssmax  timeslices  invol_ctxsw  usertime  ...  guest_time  exitcode  delayacct_blkio_time  processor
    0  0.239197    0.259398     0.260517  0.260960  ...         0.0       0.0                   0.0        0.0
    1  0.154595   -0.079616    -0.073984 -0.069349  ...        -0.0      -0.0                  -0.0       -0.0
    2  0.216759    0.211717     0.211045  0.210142  ...         0.0       0.0                   0.0        0.0

    [3 rows x 29 columns]

    # Above you see that the dataframe is sorted on the last row values
    # The last row is a weighted score determined by multiplying the
    # first row (abs value) by it's PCA variance ratio, and the second by it's
    # variance ratio, summing the values and then dividing by the sum of the
    # variance ratios to normalize the values. Since, the first row's weight is 
    # significantly higher than the second, the final score is close
    # to the abs value of the first row to the first order of approximation


    >>> sorted_features
    [('rssmax', 0.2168), ('timeslices', 0.2117), ('invol_ctxsw', 0.211), ('usertime', 0.2101), ('rdtsc_duration', 0.2101), ('cancelled_write_bytes', 0.21), ('cpu_time', 0.2097), ('time_oncpu', 0.2097), ('PERF_COUNT_SW_CPU_CLOCK', 0.2097), ('duration', 0.2088), ('systemtime', 0.2077), ('time_waiting', 0.2077), ('syscw', 0.1985), ('inblock', 0.1906), ('syscr', 0.1741), ('vol_ctxsw', 0.1716), ('write_bytes', 0.1713), ('wchar', 0.1707), ('read_bytes', 0.1675), ('rchar', 0.1534), ('minflt', 0.0968), ('outblock', 0.0), ('num_threads', 0.0), ('num_procs', 0.0), ('majflt', 0.0), ('guest_time', 0.0), ('exitcode', 0.0), ('delayacct_blkio_time', 0.0), ('processor', 0.0)]

    '''
    from epmt_stat import dframe_append_weighted_row

    jobs_df = eq.get_jobs(jobs, fmt='pandas')
    (_, variances, _, features_df) = pca_feature_combine(jobs_df, inp_features)
    weights = variances / variances.sum()
    logger.debug('normalized weights: {}'.format(list(weights)))
    # sort dataframe returned by dframe_append_weighted_row based on the values
    # in the last row
    sorted_df = dframe_append_weighted_row(features_df, weights, use_abs = True).sort_values(features_df.shape[0], axis=1, ascending=False).round(4)
    sorted_features = list(zip(sorted_df.iloc[-1].index, sorted_df.iloc[-1].round(4)))
    return (sorted_df, sorted_features)

def feature_scatter_plot(jobs, features = [], outfile='', annotate = False):
    '''
    Create a 2-D scatter plot showing job features::Outlier Detection

    Generates a 2-D scatter plot of jobs with features on two axes.
    If more than 2 features are requested, for example by setting
    features=[], then 2-component PCA analysis is automatically
    done, prior to plotting the features.

    Parameters
    ----------
           jobs : list of strings or list of Job objects or ORM or dataframe
                  Collection of jobs
        features: list of strings, optional
                  The list of features to use. If more than two features
                  are specified, PCA will be performed to get a final
                  of 2 PCA features
                  [] or '*' imply all features, and, again, PCA will be done
                  if more than two features are found. By default,
                  features is set to [], so PCA analysis will be performed
                  to reduce the final feature set to 2.

        outfile : string, optional
                  If this is set, the output is saved in a file. Otherwise
                  matplotlib's standard renderer is used.

       annotate : boolean, optional
                  If set, annotate each datapoint (plot can become cluttered if enabled)

    Example
    -------
    # The following does PCA automatically as we select *all* features as input
    >>> feature_scatter_plot(['625151', '627907', '629322', '633114', '675992', '680163', '685001', '691209', '693129'], features=[])
    # The following selects two features
    >>> feature_scatter_plot(['625151', '627907', '629322', '633114', '675992', '680163', '685001', '691209', '693129'], features=['cpu_time', 'duration'])
    '''
    jobs_df = eq.get_jobs(jobs, fmt='pandas')
    features = sanitize_features(features, jobs_df)
    title_ex = ''  # extention to append to the title on the plot
    pca_variances = None
    if len(features) > 2:
        logger.info('Performing 2-component PCA as input features({}) more than 2'.format(features))
        (jobs_pca_df, pca_variances, pca_features, _) = pca_feature_combine(jobs_df, features, desired=2)
        logger.info('{} PCA components obtained: {}'.format(len(pca_features), pca_features))
        logger.info('PCA variances: {}, sum={})'.format(pca_variances, np.sum(pca_variances)))
        jobs_df = jobs_pca_df
        features = pca_features
    if len(features) != 2:
        logger.error('Cannot generate scatter plot as requested features ({}) < 2'.format(features))
        return False
    import matplotlib as mpl
    if outfile:
        mpl.use('agg')
    import matplotlib.pyplot as plt
    import matplotlib.colors as pltc
    from random import sample
    all_colors = [k for k,v in pltc.cnames.items()]
    x_label_ext = ''
    if pca_variances is not None:
        pca_01_weight = round(pca_variances[0]/pca_variances[1], 1)
        fig = plt.figure(figsize = (max(pca_01_weight*4, 12),4))
        x_label_ext = ' (weight: {})'.format(pca_01_weight)
    else:
        fig = plt.figure(8, 8)
    ax = fig.add_subplot(1,1,1) 
    ax.set_xlabel(features[0] + x_label_ext, fontsize = 10)
    ax.set_ylabel(features[1], fontsize = 10)
    ax.set_title('2-feature plot', fontsize = 15)
    jobids = list(jobs_df['jobid'].values)
    colors = sample(all_colors, len(jobids))
    idx = 0
    for jobid in jobids:
        indexToKeep = jobs_df['jobid'] == jobid
        x = jobs_df.loc[indexToKeep, features[0]]
        y = jobs_df.loc[indexToKeep, features[1]]
        ax.scatter(x, y, c = colors[idx], s = 50)
        if annotate:
            ax.text(x+0.1, y+0.1, jobid, fontsize=8)
        idx += 1
    ax.legend(jobids, loc='upper center', bbox_to_anchor=(0.5, 1.05),
          ncol=3, fancybox=True, shadow=True)
    ax.grid()
    if outfile:
        print('plot saved to {}'.format(outfile))
        plt.savefig(outfile)
    else:
        plt.show()

    
# Sanitize feature list by removing blacklisted features
# and allowing only features whose columns have int/float types
# f: feature list
# df: jobs dataframe
# model: reference model
def sanitize_features(f, df, model = None):
    '''
    Prune feature list based on availability::Miscellaneous

    This function will prune a given list of features to a, possibly,
    smaller list by checking availability, removing blacklisted
    features, etc.

    Parameters
    ----------
             f : list of strings or '*'
                 Input list of features. [] or '*' means use all available
                 features

            df : dataframe
                 Job dataframe
         model : int or ReferenceModel object, optional

    Returns
    -------
    list of strings that is a subset of the input features
    '''
    # logger.debug('dataframe shape: {}'.format(df.shape))
    if f in ([], '', '*', None):
        logger.debug('using all available features in dataframe')
        f = set(df.columns.values)
    else:
        logger.debug('Choosing common features between: {} and {}'.format(f, df.columns.values))
        f = set(f) & set(df.columns.values)

    if model is not None:
        model_id = model.id if (type(model) != int) else model
        model_metrics = eq.refmodel_get_metrics(model_id, active_only = True)
        # take the intersection set
        logger.debug('Choosing intersection of features with model metrics ({})'.format(model_metrics))
        f &= model_metrics

    # remove blacklisted features
    _blacklisted_features = f & set(settings.outlier_features_blacklist)
    if _blacklisted_features:
        logger.debug('Pruning blacklisted features: {}'.format(_blacklisted_features))
        f -= set(settings.outlier_features_blacklist)

    features = []
    # only allow features that have int/float types
    for c in f:
        if df[c].dtype in ('int64', 'float64'):
            features.append(c)
        else:
            logger.debug('skipping feature({0}) as type is not int/float'.format(c))
    if not features:
        raise RuntimeError("Need a non-empty list of features for outlier detection")

    features = sorted(features)
    logger.debug('input features: {0}'.format(features))
    # print('features: {0}'.format(features))
    return features


def get_feature_distributions(jobs, features = []):
    '''
    Get feature distributions for a collection of jobs::Jobs

    Get the distribution (normal, uniform, etc) of features across
    a collection of jobs. If features is unspecified, all available
    numeric features will be used. The function returns a dictionary
    indexed by feature where the value is a string like 'norm' or
    'uniform'. The distribution name is a string from scipy.stats.

    Parameters
    ----------
        jobs : list of strings or list of Job objects or ORM query

    features: list of strings, optional
              A list of *numeric* features for which we want to 
              determine the the distribution. The argument is optional, 
              and if not specified, all available numeric features for the
              jobs will be used.

    Returns
    -------
    Dictionary indexed by feature where the value is the
    distribution specified as a string. At present, this string
    is one of: ['norm', 'uniform', 'unknown']

    Examples
    --------
   
    # Below we explicitly choose two features: cpu_time and rssmax. If we do not specify
    # the features, all the numeric features are selected. 
    >>> eod.get_feature_distributions(['kern-6656-20190614-190245', 'kern-6656-20190614-191138', 'kern-6656-20190614-192044-outlier', 'kern-6656-20190614-194024'], features=['cpu_time', 'rssmax'])                
    {'cpu_time': 'unknown', 'rssmax': 'norm'}

    '''
    eq._empty_collection_check(jobs)
    eq._warn_incomparable_jobs(jobs)

    # if we don't have a dataframe, get one
    if type(jobs) != pd.DataFrame:
        jobs = eq.conv_jobs(jobs, fmt='pandas')

    features = sanitize_features(features, jobs)
    dist_dict = {}
    from epmt_stat import check_dist
    for c in features:
        logger.debug('determining distribution of feature {}'.format(c))
        v = jobs[c].to_numpy()
        logger.debug('feature vector: {}'.format(v))
        v_dist = 'unknown'
        for dist in ['norm', 'uniform']:
            (passed, failed) = check_dist(v, dist)
            if passed > failed:
                v_dist = dist
                break
        dist_dict[c] = v_dist
        logger.debug('{} -> {}'.format(c, v_dist))
    return dist_dict


# Raise an exception if the length of a collection is less than
# min_length
def _err_col_len(c, min_length = 1, msg = None):
    l = orm_col_len(c)
    if l < min_length:
        msg = msg or "length of collection is less than the minimum ({0})".format(min_length)
        logger.warning(msg)
        raise RuntimeError(msg)

