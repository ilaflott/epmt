from __future__ import print_function
from epmt_query import get_jobs, get_procs, get_refmodels, get_thread_metrics, get_job_proc_tags, get_op_metrics
from logging import getLogger
from epmtlib import kwargify
from sys import stderr
from pandas import DataFrame
#import pandas
logger = getLogger(__name__)  # you can use other name

def epmt_list(arglist):
    logger.info("epmt_list: %s",str(arglist))
    if not arglist:
        return(epmt_list_jobs(arglist))
    if arglist[0] == "jobs":
        arglist = arglist[1:]
        return(epmt_list_jobs(arglist))
    if arglist[0] == "refmodels":
        arglist = arglist[1:]
        return(epmt_list_refmodels(arglist))
    if arglist[0] == "procs":
        arglist = arglist[1:]
        return(epmt_list_procs(arglist))
    if arglist[0] == "thread_metrics":
        arglist = arglist[1:]
        return(epmt_list_thread_metrics(arglist))
    if arglist[0] == "op_metrics":
        arglist = arglist[1:]
        return(epmt_list_op_metrics(arglist))
    if arglist[0] == "job_proc_tags":
        arglist = arglist[1:]
        return(epmt_list_job_proc_tags(arglist))
    return(epmt_list_jobs(arglist))

def epmt_list_jobs(arglist):
    logger.info("epmt_list_jobs: %s",str(arglist))
    kwargs = kwargify(arglist)
    if kwargs.get('fmt') == None:
        kwargs['fmt'] = 'terse'
    jobs = get_jobs(**kwargs)
#    if type(jobs) == pandas.core.frame.DataFrame:
    if len(jobs) == 0:
        logger.info("get_jobs %s returned no jobs",str(kwargs))
        return False
    print(jobs)
    return True

def epmt_list_procs(arglist):
    logger.info("epmt_list_jobs: %s",str(arglist))
    kwargs = kwargify(arglist)
    jobs = get_procs(**kwargs)
    if len(jobs) == 0:
        logger.info("get_procs %s returned no processes",str(kwargs))
        return False
    print(jobs)
    return True

def epmt_list_thread_metrics(arglist):
    logger.info("epmt_list_thread_metrics: %s",str(arglist))
    arglist = list(map(int, arglist))
    tm = get_thread_metrics(arglist)
    if tm.empty:
        logger.info("get_thread_metrics %s returned no thread metrics",str(arglist))
        return False
    print(tm)
    return True

def epmt_list_op_metrics(arglist):
    if not arglist:
        print('You must to specify one more more jobs to get op_metrics', file=stderr)
        return False
    logger.info("epmt_list_op_metrics: %s",str(arglist))
    kwargs = kwargify(arglist)
    ops = get_op_metrics(**kwargs)
    if (type(ops) != DataFrame) or (len(ops) == 0):
        logger.info("get_op_metrics %s returned no op metrics",str(kwargs))
        return False
    print(ops)
    return True

def epmt_list_refmodels(arglist):
    logger.info("epmt_list_refmodels: %s",str(arglist))
    kwargs = kwargify(arglist)
    jobs = get_refmodels(**kwargs)
    if len(jobs) == 0:
        logger.info("get_refmodels %s return no refmodels",str(kwargs))
        return False
    print(jobs)
    return True

def epmt_list_job_proc_tags(arglist):
    logger.info("epmt_list_job_proc_tags: %s",str(arglist))
    kwargs = kwargify(arglist)
    jobs = get_job_proc_tags(**kwargs)
    if len(jobs) == 0:
        logger.info("get_job_proc_tags %s returned no tags",str(kwargs))
        return False
    print(jobs)
    return True

