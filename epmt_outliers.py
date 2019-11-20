from __future__ import print_function
from os import environ
import pandas as pd
import numpy as np
import operator
from logging import getLogger
from json import dumps, loads
from orm import db_session, ReferenceModel, orm_get, orm_col_len

# the first epmt import must be epmt_query as it sets up logging
import epmt_query as eq
from epmtlib import tags_list, tag_from_string, dict_in_list, isString
from epmt_stat import thresholds, modified_z_score,outliers_iqr,outliers_modified_z_score,rca

logger = getLogger(__name__)  # you can use other name
import epmt_settings as settings

FEATURES = settings.outlier_features


def partition_jobs(jobs, features=FEATURES, methods=[modified_z_score], thresholds=thresholds, fmt='pandas'):
    """
    This function partitions jobs using one feature at a time
    INPUT: jobs is a collection/list of jobs/jobids
    OUTPUT: dictionary where the keys are features and the values
            are tuples of the form: ([ref_jobs], [outlier_jobs])
    
    >> parts = eod.partition_jobs(jobs)
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
    This function attempts to partition the supplied jobs into two partitions:
    reference jobs and outliers. The partitioning is done for each tag, and
    for a tag, if any feature makes a job an outlier then it's put in the
    outlier partition.
    
    INPUT:
      - jobs: Jobs collection specified as a list of a jobs, a single job or a pandas df
      - tags: One or more tags specified as a list of strings, or a list of dicts.
              Single tag specified as a string or tag is also acceptable.
              If not specified all the unique process tags across all jobs in "jobs"
              will be assumed.
      - features: One or more features. Specified as a list of strings
      - methods: One or more methods for outlier detection (default is MADZ)
      - thresholds: dict of constants indexable by the names of functions specified in 'methods'
    
    OUTPUT:
      - dictionary where each key is a tag, and the value is a tuple like 
        ([ref_jobs],[outlier_jobs).
    
    EXAMPLE:
    >>> jobs = eq.get_jobs(tags = 'exp_name:linux_kernel', fmt='terse)
    >>> parts = eod.partition_jobs_by_ops(jobs)
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
    >>> parts = eod.partition_jobs_by_ops(jobs, tags = 'op:build;op_instance:4;op_sequence:4')
    >>> pprint(parts)
    {'{"op_instance": "4", "op_sequence": "4", "op": "build"}': (set([u'kern-6656-20190614-190245',
                                                                  u'kern-6656-20190614-191138',
                                                                  u'kern-6656-20190614-194024']),
                                                              set([u'kern-6656-20190614-192044-outlier']))}
    """
    (_, parts, _, _, _) = detect_outlier_ops(jobs, tags=tags, features=features, methods=methods, thresholds=thresholds)
    return parts


@db_session
def detect_outlier_jobs(jobs, trained_model=None, features = FEATURES, methods=[modified_z_score], thresholds = thresholds, sanity_check=True):
    """
    This function will detects outliers among a set of input jobs
    
    INPUT:
    jobs:     is either a pandas dataframe of job(s) or a list of job ids or 
              a Pony Query object

    trained_model: The ID of a reference model (optional). If not specified,
              outlier detection will be done from within the jobs. Without
              a trained model, you will need a minimum number of jobs (4)
              for outlier detection to work.

    features: is a list of metrics available in the jobs. If an empty 
              list/None/'*' is specified, then it's assumed that the 
              user wants outlier detection on all *available* features. 
              If features is not specified, then the default 
              outlier_features in settings will be used.

    methods:  This is an advanced option to specify the function(s) to use
              for outlier detection.

    thresholds: Advanced option defining what it means to be an outlier.
              This is ordered in the same order as 'methods', and has 
              meaning in the context of the 'method' it applies to.

    sanity_check: Warn if the jobs are not comparable. Enabled by default.
    
    OUTPUT:
      (df, partitions_dict)
    
    Where "df" is a dataframe like shown below.
    The partitions dictionary is is indexed by one of the requested "features"
    and the value is a tuple like ([ref_jobs], [outlier_jobs])
    
    EXAMPLE:
    >>> jobs = eq.get_jobs(fmt='orm', tags='exp_name:linux_kernel') 
    >>> len(jobs)
    4
    >>> (df, parts) = eod.detect_outlier_jobs(jobs)
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
    """
    eq._empty_collection_check(jobs)
    if sanity_check:
        eq._warn_incomparable_jobs(jobs)

    # if we don't have a dataframe, get one
    if type(jobs) != pd.DataFrame:
        jobs = eq.conv_jobs(jobs, fmt='pandas')

    model_params = {}
    if trained_model:
        logger.debug('using a trained model for detecting outliers')
        if type(trained_model) == int:
            trained_model = orm_get(ReferenceModel, trained_model)
    else:
        _err_col_len(jobs, 4, 'Too few jobs to do outlier detection. Need at least 4!')

    for m in methods:
        model_params[m] = trained_model.computed[m.__name__] if trained_model else {}

    # sanitize features list
    features = _sanitize_features(features, jobs)

    # initialize a df with all values set to False
    retval = pd.DataFrame(0, columns=features, index=jobs.index)
    for c in features:
        # print('data-type for feature column {0} is {1}'.format(c, jobs[c].dtype))
        for m in methods:
            params = model_params[m].get(c, ())
            if params:
                logger.debug('params[{0}][{1}]: {2}'.format(m.__name__, c, params))
            scores = m(jobs[c], params)[0]
            # use the max score in the refmodel if we have a trained model
            # otherwise use the default threshold for the method
            threshold = params[0] if params else thresholds[m.__name__]
            outlier_rows = np.where(np.abs(scores) > threshold)[0]
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
    return (retval, parts)
        

@db_session
def detect_outlier_ops(jobs, tags=[], trained_model=None, features = FEATURES, methods=[modified_z_score], thresholds=thresholds, sanity_check=True):
    """
    jobs is a list of jobids or an ORM query
    tags is a list of tags specified either as a string or a list of string/list of dicts
    If tags is not specified, then the list of jobs will be queried to get the
    superset of unique tags across the jobs.
    
    OUTPUT:
     (df, dict_of_partitions, scores_df, sorted_tags, sorted_features)
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
    
    e.g.,
    jobs = [u'625151', u'627907', u'629322', u'633114', u'675992', u'680163', u'685001', u'691209', u'693129', u'696110', u'802938', u'804266']
    
    
    >>> (df, parts, scores_df, sorted_tags, sorted_features) = eod.detect_outlier_ops(jobs)
    
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
    """
    eq._empty_collection_check(jobs)
    if sanity_check:
        eq._warn_incomparable_jobs(jobs)

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
   
    for t in tags_to_use:
        t = dumps(t, sort_keys=True)
        model_params[t] = {}
        for m in methods:
            model_params[t][m] = trained_model.computed[t][m.__name__] if trained_model else {}


    # get the dataframe of aggregate metrics, where each row
    # is an aggregate across a group of processes with a particular
    # jobid and tag
    ops = eq.op_metrics(jobs=jobs, tags=tags_to_use)
    if len(ops) == 0:
        logger.warning('no matching tags found in the tag set: {0}'.format(tags_to_use))
        return (None, {})
    features = _sanitize_features(features, ops)
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
        logger.debug('Processing tag: {0}'.format(tag))
        # select only those rows with matching tag
        rows = ops[ops.tags == tag]
        # logger.debug('input: \n{0}\n'.format(rows[['tags']+features]))
        tags_max[t] = []
        for c in features:
            score_diff = 0
            for m in methods:
                params = model_params[t][m].get(c, ())
                # if params:
                #     logger.debug('params[{0}][{1}][{2}]: {3}'.format(t,m.__name__, c, params))
                scores = m(rows[c], params)[0]
                # use the max score in the refmodel if we have a trained model
                # otherwise use the default threshold for the method
                threshold = params[0] if params else thresholds[m.__name__]
                outlier_rows = np.where(np.abs(scores) > threshold)[0]
                score_diff += max(max(scores) - threshold, 0)
                # remain the outlier rows indices to the indices in the original df
                outlier_rows = rows.index[outlier_rows].values
                logger.debug('outliers for [{0}][{1}][{2}] -> {3}'.format(t,m.__name__,c,outlier_rows))
                retval.loc[outlier_rows,c] += 1
            tags_max[t].append(round(score_diff, 3))
    retval['jobid'] = ops['job']
    retval['tags'] = ops['tags']
    retval = retval[['jobid', 'tags']+features]

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

    
def detect_outlier_processes(processes, trained_model=None, 
                             features=['duration','exclusive_cpu_time'],
                             methods=[outliers_iqr,outliers_modified_z_score]):
    """
    This function detects outlier processes using either a trained model
    or from within the input set.
    """
    eq._empty_collection_check(processes)
    retval = pd.DataFrame(0, columns=features, index=processes.index)
    for c in features:
        for m in methods:
            outlier_rows = m(processes[c])
            print(m.__name__,c,len(outlier_rows),"outliers")
            retval.loc[outlier_rows,c] += 1
#
#   Here we can demand that more than one detector signal an outlier, currently only 1 is required.
#
    # print(retval.describe())
    print(retval.head())
    retval = retval.gt(.99)
    retval['id'] = processes['id']
    retval['exename'] = processes['exename']
    retval['tags'] = processes['tags']
    retval = retval[['id','exename','tags']+features]
    return retval



@db_session
def detect_rootcause(jobs, inp, features = FEATURES,  methods = [modified_z_score]):
    """
    This function does an RCA for outlier jobs

    INPUT:
    jobs is either a dataframe of reference jobs, or a list
    of reference jobs, or a trained model.
    inp is either a single job/jobid or a Series or a dataframe with a single column

    OUTPUT:
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
    This function does an RCA for outlier ops

    INPUT:
    jobs is either a dataframe of reference jobs, or a list
    of reference jobs, or a trained model.
    inp is either a single job/jobid or a Series or a dataframe with a single column
    tag: Required string or dictionary signifying the operation
    
    OUTPUT:
        (res, df, sorted_feature_list),
    where 'res' is True on sucess and False otherwise,
    df is a dataframe that ranks the features from left to right according
    to the difference of the score for the input with the score for the reference
    for the feature. The sorted_tuples consists of a list of tuples, where each
    tuple (feature,<diff_score>)
    
    EXAMPLE:
    (retval, df, s) = eod.detect_rootcause_op([u'kern-6656-20190614-190245', u'kern-6656-20190614-191138', u'kern-6656-20190614-194024'], u'kern-6656-20190614-192044-outlier', tag = 'op_sequence:4')
    
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
    ref_ops_df = eq.op_metrics(jobs, tag)
    inp_ops_df = eq.op_metrics(inp, tag)
    unique_tags = set([str(d) for d in ref_ops_df['tags'].values])
    if unique_tags != set([str(tag)]):
        # this is just a sanity check to make sure we only compare
        # rows that have the same tag. Ordinarily this code won't be
        # triggered as eq.op_metrics will only return rows that match 'tag'
        print('ref jobs have multiple distinct tags({0}) that are superset of this specified tag. Please specify an exact tag match'.format(unique_tags))
        return (False, None, None)
    return rca(ref_ops_df, inp_ops_df, features, methods)


# Sanitize feature list by removing blacklisted features
# and allowing only features whose columns have int/float types
def _sanitize_features(f, df):
    if f in ([], '', '*', None):
        logger.debug('using all available features in outlier detection')
        f = set(df.columns.values) 
    f = set(f) - set(settings.outlier_features_blacklist)
    features = []
    # only allow features that have int/float types
    for c in f:
        if df[c].dtype in ('int64', 'float64'):
            features.append(c)
        else:
            logger.debug('skipping feature({0}) as type is not int/float'.format(c))
    logger.info('using features: {0}'.format(features))
    return features

# Raise an exception if the length of a collection is less than
# min_length
def _err_col_len(c, min_length = 1, msg = None):
    l = orm_col_len(c)
    if l < min_length:
        msg = msg or "length of collection is less than the minimum ({0})".format(min_length)
        logger.warning(msg)
        raise RuntimeError(msg)


if (__name__ == "__main__"):
    np.random.seed(101)
    random_data = np.random.randn(100,2)
    random_proc_df = pd.DataFrame(random_data, columns=['duration','exclusive_cpu_time'])
    random_proc_df['id'] = ""
    random_proc_df['exename'] = ""
    random_proc_df['tags'] = ""
    retval = detect_outlier_processes(random_proc_df)
    print(retval.head())
#
# Here we print a boolean if any metric barfed at us
#
    print ((retval[['duration','exclusive_cpu_time']] == True).any(axis=1).head())
