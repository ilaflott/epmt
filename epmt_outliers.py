import pandas as pd
import numpy as np
import epmt_query as eq
from pony.orm.core import Query

# These all return a tuple containing a list of indicies
# For 1-D this is just a tuple with one element that is a list of rows
def outliers_z_score(ys):
    threshold = 3
    mean_y = np.mean(ys)
    stdev_y = np.std(ys)
    z_scores = [(y - mean_y) / stdev_y for y in ys]
    return np.where(np.abs(z_scores) > threshold)
def outliers_iqr(ys, range=[30,70]):
    quartile_1, quartile_3 = np.percentile(ys, range)
    iqr = quartile_3 - quartile_1
    lower_bound = quartile_1 - (iqr * 1.5)
    upper_bound = quartile_3 + (iqr * 1.5)
    return np.where((ys > upper_bound) | (ys < lower_bound))
def outliers_modified_z_score(ys,threshold=2.5):
    median_y = np.median(ys)
    median_absolute_deviation_y = np.median([np.abs(y - median_y) for y in ys])
    modified_z_scores = [0.6745 * (y - median_y) / median_absolute_deviation_y
                         for y in ys]
    return np.where(np.abs(modified_z_scores) > threshold)

def get_outlier_1d(df,column,func=outliers_iqr):
    if column not in df:
        return None
    return(func(df[column]))

def get_outlier_jobs(df,columns=["duration","cputime"]):
    return None

def get_outliers_operations(df,columns=["duration","cputime"]):
    return None

def get_outliers_processes(df,columns=["duration","exclusive_cpu_time"]):
    return None

# jobs is either a pandas dataframe of job(s) or a list of job ids
# or a Pony Query object
def detect_outlier_jobs(jobs, trained_model=None, features = ['duration','cpu_time','num_procs']):
    # if we have a non-empty list of job ids then get a pandas df
    # using get_jobs to convert the format
    if type(jobs) == list or type(jobs) == Query:
        jobs = eq.get_jobs(jobs, fmt='pandas')

    # initialize a df with all values set to False
    retval = pd.DataFrame(False, columns=features, index=jobs.index)
    for c in features:
        outlier_rows = outliers_iqr(jobs[c])[0]
#        print(c,outlier_rows)
        retval.loc[outlier_rows,c] = True
    # add a jobid column to the output dataframe
    retval['jobid'] = jobs['jobid']
    retval = retval[['jobid']+features]
    return retval

# jobs is a list of jobids or a Pony Query object
# tags is a list of tags specified either as a string or a list of string/list of dicts
# If tags is not specified, then the list of jobs will be queried to get the
# superset of unique tags across the jobs.
# This function should effectively replace detect_outlier_ops as
# it requires less user steps
def detect_outlier_jobs_using_tags(jobs, tags=[], trained_model=None, features = ['duration','exclusive_cpu_time','num_procs','majflt','rssmax']):
    if not tags:
        tags = eq.get_unique_process_tags(jobs, fold=False)
    # get the dataframe of aggregate metrics, where each row
    # is an aggregate across a group of processes with a particular
    # jobid and tag
    ops = eq.agg_metrics_by_tags(jobs=jobs, tags=tags) 
    retval = pd.DataFrame(False, columns=features, index=ops.index)

    # now we iterate over tags and for each tag we select
    # the rows from the ops dataframe that have the same tag;
    # the select rows will have different job ids
    for tag in tags:
        # select only those rows with matching tag
        rows = ops[ops.tags == tag]
        for c in features:
            outlier_rows = outliers_iqr(rows[c])[0]
            retval.loc[outlier_rows,c] = True
    retval['jobid'] = ops['job']
    retval['tags'] = ops['tags']
    retval = retval[['jobid', 'tags']+features]
    return retval


def detect_outlier_ops(ops, tags, trained_model=None, features = ['duration','exclusive_cpu_time','num_procs']):
    
    retval = pd.DataFrame(False, columns=features, index=ops.index)
    for tag in tags:
        # select only those rows with matching tag
        rows = ops[ops.tags == tag]
        for c in features:
            outlier_rows = outliers_iqr(rows[c])[0]
            retval.loc[outlier_rows,c] = True
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
            outlier_rows = m(processes[c])[0]
            print(m,c,len(outlier_rows),"outliers")
            retval.loc[outlier_rows,c] += 1
#
#   Here we can demand that more than one detector signal an outlier, currently only 1 is required.
#
    print retval.head()
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
    print retval.head()
#
# Here we print a boolean if any metric barfed at us
#
    print ((retval[['duration','exclusive_cpu_time']] == True).any(axis=1)).head()
