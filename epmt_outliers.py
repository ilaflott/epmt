import pandas as pd
import numpy as np

# These all return a tuple containing a list of indicies
# For 1-D this is just a tuple with one element that is a list of rows
def outliers_z_score(ys):
    threshold = 3
    mean_y = np.mean(ys)
    stdev_y = np.std(ys)
    z_scores = [(y - mean_y) / stdev_y for y in ys]
    return np.where(np.abs(z_scores) > threshold)
def outliers_iqr(ys):
    quartile_1, quartile_3 = np.percentile(ys, [10, 90])
    iqr = quartile_3 - quartile_1
    lower_bound = quartile_1 - (iqr * 1.5)
    upper_bound = quartile_3 + (iqr * 1.5)
    return np.where((ys > upper_bound) | (ys < lower_bound))
def outliers_modified_z_score(ys):
    threshold = 3.5
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

def detect_outlier_jobs(jobs, trained_model=None, features = ['duration','cpu_time','num_procs']):
    retval = pd.DataFrame(columns=features, index=jobs.index)
    for c in features:
        outlier_rows = eod.outliers_iqr(jobs[c])[0]
#        print(c,outlier_rows)
        retval.loc[outlier_rows,c] = True
    retval['jobid'] = jobs['jobid']
    retval = retval[['jobid']+features]
    return retval

def detect_outlier_ops(ops, trained_model=None, features = ['duration','exclusive_cpu_time','num_procs']):
    retval = pd.DataFrame(columns=features, index=ops.index)
    for c in features:
        outlier_rows = eod.outliers_iqr(ops[c])[0]
#        print(c,outlier_rows)
        retval.loc[outlier_rows,c] = True
    retval['jobid'] = ops['jobid']
    retval = retval[['jobid']+features]
    return retval

def detect_outlier_processes(processes, trained_model=None, features=['duration','exclusive_cpu_time']):
    retval = pd.DataFrame(columns=features, index=processes.index)
    for c in features:
        outlier_rows = eod.outliers_iqr(processes[c])[0]
        print(c,outlier_rows)
        retval.loc[outlier_rows,c] = True
    retval['id'] = processes['id']
    retval['exename'] = processes['exename']
    retval['tags'] = processes['tags']
    retval = retval[['id','exename','tags']+features]
    return retval
