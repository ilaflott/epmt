from __future__ import print_function
from os import environ
import pandas as pd
import numpy as np
import epmt_query as eq
from pony.orm.core import Query
from models import ReferenceModel
from logging import getLogger
from json import dumps
from epmt_job import dict_in_list

logger = getLogger(__name__)  # you can use other name

if environ.get('EPMT_USE_DEFAULT_SETTINGS'):
    #logger.info('Overriding settings.py and using defaults in epmt_default_settings')
    import epmt_default_settings as settings
else:
    import settings



# this sets the defaults to be used when a trained model is not provided
THRESHOLDS = settings.outlier_thresholds if hasattr(settings, 'outlier_thresholds') else { 'modified_z_score': 2.5, 'iqr': [20,80], 'z_score': 3.0 }
FEATURES = settings.outlier_features if hasattr(settings, 'outlier_features') else ['duration', 'cpu_time', 'num_procs']

# These all return a tuple containing a list of indicies
# For 1-D this is just a tuple with one element that is a list of rows
def outliers_z_score(ys, threshold=THRESHOLDS['z_score']):
    mean_y = np.mean(ys)
    stdev_y = np.std(ys)
    z_scores = [(y - mean_y) / stdev_y for y in ys]
    return np.where(np.abs(z_scores) > threshold)[0]

def outliers_iqr(ys, span=THRESHOLDS['iqr']):
    quartile_1, quartile_3 = np.percentile(ys, span)
    iqr = quartile_3 - quartile_1
    lower_bound = quartile_1 - (iqr * 1.5)
    upper_bound = quartile_3 + (iqr * 1.5)
    return np.where((ys > upper_bound) | (ys < lower_bound))[0]

# this function returns a tuple consisting of:
#  (modified_z_scores, max, median, median_abs_dev)
# The reason we return max,.. is so it can be saved in the ref model
# params if passed in, is of the form (max, median, median_abs_dev)
# We will ignore params(0) as that's the max z_score in the ref_model
def modified_z_score(ys, params=()):
    median_y = params[1] if params else np.median(ys)
    median_absolute_deviation_y = params[2] if params else np.median([np.abs(y - median_y) for y in ys])
    # z_score will be zero if std. dev is zero, for all others compute it
    modified_z_scores = [round(0.6745 * abs(y - median_y) / median_absolute_deviation_y, 4)
                         for y in ys] if median_absolute_deviation_y > 0 else [0.0 for y in ys]
    return (modified_z_scores, max(modified_z_scores), median_y, median_absolute_deviation_y)


def outliers_modified_z_score(ys,threshold=THRESHOLDS['modified_z_score']):
    scores = modified_z_score(ys)[0]
    return np.where(np.abs(scores) > threshold)[0]

def get_outlier_1d(df,column,func=outliers_iqr):
    if column not in df:
        return None
    return(func(df[column]))


def partition_jobs(jobs, feature='duration', methods=[modified_z_score], thresholds=THRESHOLDS, fmt='pandas'):
    if type(feature) not in [str, unicode]:
        logger.error('feature needs to be a single string such as "duration"')
        return None
    df = detect_outlier_jobs(jobs, features=[feature], methods=methods, thresholds=thresholds)
    outliers_df = df[df[feature] > 0]
    ref_df = df[df[feature] == 0]
    if fmt == 'pandas':
        return (outliers_df, ref_df)
    ref_list = list(ref_df['jobid'].values)
    outliers_list = list(outliers_df['jobid'].values)
    if fmt == 'terse':
        return (outliers_list, ref_list)
    if fmt == 'orm':
        return (eq.conv_jobs_terse(outliers_list), eq.conv_jobs_terse(ref_list))



# jobs is either a pandas dataframe of job(s) or a list of job ids or a Pony Query object
def detect_outlier_jobs(jobs, trained_model=None, features = FEATURES, methods=[modified_z_score], thresholds = THRESHOLDS):
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
    return retval

# jobs is a list of jobids or a Pony Query object
# tags is a list of tags specified either as a string or a list of string/list of dicts
# If tags is not specified, then the list of jobs will be queried to get the
# superset of unique tags across the jobs.
def detect_outlier_ops(jobs, tags=[], trained_model=None, features = FEATURES, methods=[modified_z_score], thresholds=THRESHOLDS):

    # do we have a single tag in string or dict form? 
    if type(tags) == str:
        tags = [eq.get_tags_from_string(tags)]
    elif type(tags) == dict:
        tags = [tags]
    tags = [eq.get_tags_from_string(t) for t in tags if type(t) == str]
        
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
    ops = eq.agg_metrics_by_tags(jobs=jobs, tags=tags_to_use) 
    retval = pd.DataFrame(0, columns=features, index=ops.index)

    # now we iterate over tags and for each tag we select
    # the rows from the ops dataframe that have the same tag;
    # the select rows will have different job ids
    for tag in tags_to_use:
        t = dumps(tag, sort_keys=True)
        logger.debug('Processing tag: {0}'.format(tag))
        # select only those rows with matching tag
        rows = ops[ops.tags == tag]
        logger.debug('input: \n{0}\n'.format(rows[['tags']+features]))
        for c in features:
            for m in methods:
                params = model_params[t][m].get(c, ())
                if params:
                    logger.debug('params[{0}][{1}][{2}]: {3}'.format(t,m.__name__, c, params))
                scores = m(rows[c], params)[0]
                # use the max score in the refmodel if we have a trained model
                # otherwise use the default threshold for the method
                threshold = params[0] if params else thresholds[m.__name__]
                outlier_rows = np.where(np.abs(scores) > threshold)[0]
                # remain the outlier rows indices to the indices in the original df
                outlier_rows = rows.index[outlier_rows].values
                logger.debug('Outliers for [{0}][{1}][{2}] -> {3}'.format(t,m.__name__,c,outlier_rows))
                retval.loc[outlier_rows,c] += 1
    retval['jobid'] = ops['job']
    retval['tags'] = ops['tags']
    retval = retval[['jobid', 'tags']+features]
    return retval


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
