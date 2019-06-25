from __future__ import print_function
from os import environ
import pandas as pd
import numpy as np
import operator
import epmt_query as eq
from pony.orm.core import Query
from models import ReferenceModel
from logging import getLogger
from json import dumps
from epmtlib import tags_list, tag_from_string
from epmt_job import dict_in_list
from epmt_stat import thresholds, modified_z_score,outliers_iqr,outliers_modified_z_score,rca

logger = getLogger(__name__)  # you can use other name

if environ.get('EPMT_USE_DEFAULT_SETTINGS'):
    logger.info('Overriding settings.py and using defaults in epmt_default_settings')
    import epmt_default_settings as settings
else:
    import settings

FEATURES = settings.outlier_features if hasattr(settings, 'outlier_features') else ['duration', 'cpu_time', 'num_procs']


# This function partitions jobs using one feature at a time
# INPUT: jobs is a collection/list of jobs/jobids
# OUTPUT: dictionary where the keys are features and the values
#         are tuples of the form: ([ref_jobs], [outlier_jobs])
#
#>>> parts = eod.partition_jobs(jobs)
# >>> pprint(parts)
# {'cpu_time': (set([u'kern-6656-20190614-190245',
#                u'kern-6656-20190614-194024',
#                u'kern-6656-20190614-191138']),
#               set([u'kern-6656-20190614-192044-outlier'])),
#  'duration': (set([u'kern-6656-20190614-190245',
#                u'kern-6656-20190614-194024',
#                u'kern-6656-20190614-191138']),
#               set([u'kern-6656-20190614-192044-outlier'])),
#  'num_procs': (set([u'kern-6656-20190614-190245',
#                 u'kern-6656-20190614-192044-outlier',
#                 u'kern-6656-20190614-194024',
#                 u'kern-6656-20190614-191138']),
#                set([]))}
def partition_jobs(jobs, features=FEATURES, methods=[modified_z_score], thresholds=thresholds, fmt='pandas'):
    (_,parts) = detect_outlier_jobs(jobs, features=features, methods=methods, thresholds=thresholds)
    return parts

# This function attempts to partition the supplied jobs into two partitions:
# reference jobs and outliers. The partitioning is done for each tag, and
# for a tag, if any feature makes a job an outlier then it's put in the
# outlier partition.
#
# INPUT:
#   - jobs: Jobs collection specified as a list of a jobs, a single job or a pandas df
#   - tags: One or more tags specified as a list of strings, or a list of dicts.
#           Single tag specified as a string or tag is also acceptable.
#           If not specified all the unique process tags across all jobs in "jobs"
#           will be assumed.
#   - features: One or more features. Specified as a list of strings
#   - methods: One or more methods for outlier detection (default is MADZ)
#   - thresholds: dict of constants indexable by the names of functions specified in 'methods'
#
# OUTPUT:
#   - dictionary where each key is a tag, and the value is a tuple like 
#     ([ref_jobs],[outlier_jobs).
#
# EXAMPLE:
# >>> jobs = eq.get_jobs(tag = 'exp_name:linux_kernel', fmt='terse)
# >>> parts = eod.partition_jobs_by_ops(jobs)
# >>> pprint(parts)
# {'{"op_instance": "1", "op_sequence": "1", "op": "download"}': (set[u'kern-6656-20190614-190245',
#                                                                  u'kern-6656-20190614-191138',
#                                                                  u'kern-6656-20190614-194024']),
#                                                            set[u'kern-6656-20190614-192044-outlier'])),
#  '{"op_instance": "2", "op_sequence": "2", "op": "extract"}': (set([u'kern-6656-20190614-190245',
#                                                                 u'kern-6656-20190614-191138',
#                                                                 u'kern-6656-20190614-194024']),
#                                                            set([u'kern-6656-20190614-192044-outlier'])),
# ...
# }
#
#
# In the example above we did not supply any tags so the set of unique
# process tags was determined automatically. We can also choose to
# specify a tag (or a list of tags) as so:
# >>> parts = eod.partition_jobs_by_ops(jobs, tags = 'op:build;op_instance:4;op_sequence:4')
# >>> pprint(parts)
# {'{"op_instance": "4", "op_sequence": "4", "op": "build"}': (set([u'kern-6656-20190614-190245',
#                                                               u'kern-6656-20190614-191138',
#                                                               u'kern-6656-20190614-194024']),
#                                                           set([u'kern-6656-20190614-192044-outlier']))}

def partition_jobs_by_ops(jobs, tags=[], features=FEATURES, methods=[modified_z_score], thresholds=thresholds):
    (_, parts) = detect_outlier_ops(jobs, tags=tags, features=features, methods=methods, thresholds=thresholds)
    return parts


# This function will detects outliers among a set of input jobs
#
# INPUT:
# jobs is either a pandas dataframe of job(s) or a list of job ids or a Pony Query object
# 
# OUTPUT:
#   (df, partitions_dict)
#
# Where "df" is a dataframe like shown below.
# The partitions dictionary is is indexed by one of the requested "features"
# and the value is a tuple like ([ref_jobs], [outlier_jobs])
#
# EXAMPLE:
# >>> jobs = eq.get_jobs(fmt='orm', tag='exp_name:linux_kernel') 
# >>> len(jobs)
# 4
# >>> (df, parts) = eod.detect_outlier_jobs(jobs)
# >>> df
#                                jobid  duration  cpu_time  num_procs
# 0          kern-6656-20190614-190245         0         0          0
# 1  kern-6656-20190614-192044-outlier         1         1          0
# 2          kern-6656-20190614-194024         0         0          0
# 3          kern-6656-20190614-191138         0         0          0
#
# >>> pprint(parts)
# {'cpu_time': ([u'kern-6656-20190614-190245',
#                u'kern-6656-20190614-194024',
#                u'kern-6656-20190614-191138'],
#               [u'kern-6656-20190614-192044-outlier']),
#  'duration': ([u'kern-6656-20190614-190245',
#                u'kern-6656-20190614-194024',
#                u'kern-6656-20190614-191138'],
#               [u'kern-6656-20190614-192044-outlier']),
#  'num_procs': ([u'kern-6656-20190614-190245',
#                 u'kern-6656-20190614-192044-outlier',
#                 u'kern-6656-20190614-194024',
#                 u'kern-6656-20190614-191138'],
#                [])}

def detect_outlier_jobs(jobs, trained_model=None, features = FEATURES, methods=[modified_z_score], thresholds = thresholds):
    # if we have a non-empty list of job ids then get a pandas df
    # using get_jobs to convert the format
    if type(jobs) == list or type(jobs) == Query:
        jobs = eq.get_jobs(jobs, fmt='pandas')

    model_params = {}
    if trained_model:
        logger.debug('using a trained model for detecting outliers')
        if type(trained_model) == int:
            trained_model = ReferenceModel[trained_model]

    for m in methods:
        model_params[m] = trained_model.computed[m.__name__] if trained_model else {}

    # initialize a df with all values set to False
    retval = pd.DataFrame(0, columns=features, index=jobs.index)
    for c in features:
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
        

# jobs is a list of jobids or a Pony Query object
# tags is a list of tags specified either as a string or a list of string/list of dicts
# If tags is not specified, then the list of jobs will be queried to get the
# superset of unique tags across the jobs.
#
# OUTPUT:
#  (dataframe, dict_of_partitions)
# The dict of partitions is indexed by the tag, and the value 
# is a tuple, consisting of the (<ref_part>,<outlier_part>) for the tag.
# e.g.,
#
# >>> (df, parts) = eod.detect_outlier_ops(jobs, tags = {"op_instance": "4", "op_sequence": "4", "op": "build"})
# >>> df
#                                jobid  \
# 0          kern-6656-20190614-190245   
# 1          kern-6656-20190614-191138   
# 2  kern-6656-20190614-192044-outlier   
# 3          kern-6656-20190614-194024   
# 
#                                                 tags  duration  cpu_time  \
# 0  {u'op_instance': u'4', u'op_sequence': u'4', u...         0         0   
# 1  {u'op_instance': u'4', u'op_sequence': u'4', u...         0         0   
# 2  {u'op_instance': u'4', u'op_sequence': u'4', u...         1         1   
# 3  {u'op_instance': u'4', u'op_sequence': u'4', u...         0         0   
# 
#    num_procs  
# 0          0  
# 1          0  
# 2          0  
# 3          0  
#
# >>> parts
# {'{"op_instance": "4", "op_sequence": "4", "op": "build"}': ([u'kern-6656-20190614-190245', u'kern-6656-20190614-191138', u'kern-6656-20190614-194024'], [u'kern-6656-20190614-192044-outlier'])}
#
#
# Here is another example, this time we auto-detect the tags:
# >>> jobs = eq.get_jobs(fmt='orm', tag='exp_name:linux_kernel')
# >>> (df, parts) = eod.detect_outlier_ops(jobs)
# >>> df[['jobid', 'tags', 'duration', 'cpu_time']][:5]
#                                jobid  \
# 0          kern-6656-20190614-190245   
# 1          kern-6656-20190614-191138   
# 2  kern-6656-20190614-192044-outlier   
# 3          kern-6656-20190614-194024   
# 4          kern-6656-20190614-190245   
# 
#                                                 tags  duration  cpu_time  
# 0  {u'op_instance': u'4', u'op_sequence': u'4', u...         0         0  
# 1  {u'op_instance': u'4', u'op_sequence': u'4', u...         0         0  
# 2  {u'op_instance': u'4', u'op_sequence': u'4', u...         1         1  
# 3  {u'op_instance': u'4', u'op_sequence': u'4', u...         0         0  
# 4  {u'op_instance': u'5', u'op_sequence': u'5', u...         0         0  
#
#
# >>> pprint(parts)
# {'{"op_instance": "1", "op_sequence": "1", "op": "download"}': ([u'kern-6656-20190614-190245',
#                                                                  u'kern-6656-20190614-191138',
#                                                                  u'kern-6656-20190614-194024'],
#                                                                 [u'kern-6656-20190614-192044-outlier']),
#  '{"op_instance": "2", "op_sequence": "2", "op": "extract"}': ([u'kern-6656-20190614-190245',
#                                                                 u'kern-6656-20190614-191138',
#                                                                 u'kern-6656-20190614-194024'],
#                                                                [u'kern-6656-20190614-192044-outlier']),
#  '{"op_instance": "3", "op_sequence": "3", "op": "configure"}': ([u'kern-6656-20190614-190245',
#                                                                   u'kern-6656-20190614-191138',
#                                                                   u'kern-6656-20190614-194024'],
#                                                                  [u'kern-6656-20190614-192044-outlier']),
#  '{"op_instance": "4", "op_sequence": "4", "op": "build"}': ([u'kern-6656-20190614-190245',
#                                                               u'kern-6656-20190614-191138',
#                                                               u'kern-6656-20190614-194024'],
#                                                              [u'kern-6656-20190614-192044-outlier']),
#  '{"op_instance": "5", "op_sequence": "5", "op": "clean"}': ([u'kern-6656-20190614-190245',
#                                                               u'kern-6656-20190614-191138',
#                                                               u'kern-6656-20190614-194024'],
#                                                              [u'kern-6656-20190614-192044-outlier'])}

def detect_outlier_ops(jobs, tags=[], trained_model=None, features = FEATURES, methods=[modified_z_score], thresholds=thresholds):

    tags = tags_list(tags)
        
    jobs_tags_set = set()
    unique_job_tags = eq.get_unique_process_tags(jobs, fold=False)
    for t in unique_job_tags:
        jobs_tags_set.add(dumps(t, sort_keys=True))

    model_params = {}
    if trained_model:
        model_tags_set = set()
        logger.debug('using a trained model for detecting outliers')
        if type(trained_model) == int:
            trained_model = ReferenceModel[trained_model]
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
    if not tags:
        tags = unique_job_tags

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
    retval = pd.DataFrame(0, columns=features, index=ops.index)

    # now we iterate over tags and for each tag we select
    # the rows from the ops dataframe that have the same tag;
    # the select rows will have different job ids
    for tag in tags_to_use:
        t = dumps(tag, sort_keys=True)
        logger.debug('Processing tag: {0}'.format(tag))
        # select only those rows with matching tag
        rows = ops[ops.tags == tag]
        # logger.debug('input: \n{0}\n'.format(rows[['tags']+features]))
        for c in features:
            for m in methods:
                params = model_params[t][m].get(c, ())
                # if params:
                #     logger.debug('params[{0}][{1}][{2}]: {3}'.format(t,m.__name__, c, params))
                scores = m(rows[c], params)[0]
                # use the max score in the refmodel if we have a trained model
                # otherwise use the default threshold for the method
                threshold = params[0] if params else thresholds[m.__name__]
                outlier_rows = np.where(np.abs(scores) > threshold)[0]
                # remain the outlier rows indices to the indices in the original df
                outlier_rows = rows.index[outlier_rows].values
                logger.debug('outliers for [{0}][{1}][{2}] -> {3}'.format(t,m.__name__,c,outlier_rows))
                retval.loc[outlier_rows,c] += 1
    retval['jobid'] = ops['job']
    retval['tags'] = ops['tags']
    retval = retval[['jobid', 'tags']+features]
    # partition using tags
    parts = {}
    for tag in tags_to_use:
        dft = retval[retval.tags == tag]
        q_ref = "&".join(["{0} == 0".format(f) for f in features])
        dft_ref = dft.query(q_ref).reset_index(drop=True)
        q_outlier = "|".join(["{0} > 0".format(f) for f in features])
        dft_outlier = dft.query(q_outlier).reset_index(drop=True)
        parts[dumps(tag)] = (set(dft_ref['jobid'].values), (set(dft_outlier['jobid'].values)))
    return (retval, parts)
    


def detect_outlier_processes(processes, trained_model=None, 
                             features=['duration','exclusive_cpu_time'],
                             methods=[outliers_iqr,outliers_modified_z_score]):
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


# This function does an RCA for outlier jobs
# INPUT:
# jobs is either a dataframe of reference jobs, or a list
# of reference jobs, or a trained model.
# inp is either a single job/jobid or a Series or a dataframe with a single column
# OUTPUT:
#     (res, df, sorted_feature_list),
# where 'res' is True on sucess and False otherwise,
# df is a dataframe that ranks the features from left to right according
# to the difference of the score for the input with the score for the reference
# for the feature. The sorted_tuples consists of a list of tuples, where each
# tuple (feature,<diff_score>)

def detect_rootcause(jobs, inp, features = FEATURES,  methods = [modified_z_score]):
    if type(jobs) == int:
        jobs = eq.get_jobs(ReferenceModel[jobs].jobs, fmt='pandas')
    elif type(jobs) != pd.DataFrame:
        jobs = eq.get_jobs(jobs, fmt='pandas')
    if type(inp) in [str, unicode, Query]:
        inp = eq.get_jobs(inp, fmt='pandas')
    return rca(jobs, inp, features, methods)

# This function does an RCA for outlier ops
# INPUT:
# jobs is either a dataframe of reference jobs, or a list
# of reference jobs, or a trained model.
# inp is either a single job/jobid or a Series or a dataframe with a single column
# tag: Required string or dictionary signifying the operation
#
# OUTPUT:
#     (res, df, sorted_feature_list),
# where 'res' is True on sucess and False otherwise,
# df is a dataframe that ranks the features from left to right according
# to the difference of the score for the input with the score for the reference
# for the feature. The sorted_tuples consists of a list of tuples, where each
# tuple (feature,<diff_score>)
# 
# EXAMPLE:
# (retval, df, s) = eod.detect_rootcause_op([u'kern-6656-20190614-190245', u'kern-6656-20190614-191138', u'kern-6656-20190614-194024'], u'kern-6656-20190614-192044-outlier', tag = 'op_sequence:4')
#
# >>> df
#                               cpu_time      duration  num_procs
# count                     3.000000e+00  3.000000e+00          3
# mean                      3.812180e+08  2.205502e+09       9549
# std                       4.060242e+05  4.762406e+07          0
# min                       3.808073e+08  2.158731e+09       9549
# 25%                       3.810175e+08  2.181285e+09       9549
# 50%                       3.812277e+08  2.203839e+09       9549
# 75%                       3.814234e+08  2.228887e+09       9549
# max                       3.816191e+08  2.253935e+09       9549
# input                     5.407379e+08  5.014023e+09       9549
# ref_max_modified_z_score  7.246000e-01  7.491000e-01          0
# modified_z_score          2.748777e+02  4.202000e+01          0
# modified_z_score_ratio    3.793510e+02  5.609398e+01          0
# >>> s
# [('cpu_time', 379.350952249517), ('duration', 56.09397944199707), ('num_procs', 0.0)]

def detect_rootcause_op(jobs, inp, tag, features = FEATURES,  methods = [modified_z_score]):
    if not tag:
        logger.warning('You must specify a non-empty tag')
        return (None, None)
    if type(jobs) == int:
        jobs = eq.get_jobs(ReferenceModel[jobs].jobs, fmt='orm')
    jobs = eq.__jobs_col(jobs)
    inp = eq.__jobs_col(inp)
    if len(inp) > 1:
        logger.warning('You can only do RCA for a single "inp" job')
        return (False, None, None)
    tag = tag_from_string(tag) if type(tag == str) else tag
    ref_ops_df = eq.op_metrics(jobs, tag)
    inp_ops_df = eq.op_metrics(inp, tag)
    unique_tags = set([str(d) for d in ref_ops_df['tags'].values])
    if unique_tags != set([str(tag)]):
        # this is just a sanity check to make sure we only compare
        # rows that have the same tag. Ordinarily this code won't be
        # triggered as eq.op_metrics will only return rows that match 'tag'
        logger.warning('ref jobs have multiple distinct tags({0}) that are superset of this specified tag. Please specify an exact tag match'.format(unique_tags))
        return (False, None, None)
    return rca(ref_ops_df, inp_ops_df, features, methods)
    

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
