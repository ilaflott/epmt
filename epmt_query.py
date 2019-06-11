from sys import stderr
#from __future__ import print_function
from models import *
from epmt_job import setup_orm_db, get_tags_from_string, _sum_dicts, unique_dicts, fold_dicts
import pandas as pd
from pony.orm.core import Query, set_sql_debug
from pony.orm import select, sum, count, avg, group_concat
from json import loads
from os import environ

if environ.get('EPMT_USE_DEFAULT_SETTINGS'):
    logger.info('Overriding settings.py and using defaults in epmt_default_settings')
    import epmt_default_settings as settings
else:
    import settings

print(settings.db_params)
setup_orm_db(settings)


# This function returns a list of jobs based on some filtering and ordering.
# The output format can be set to pandas dataframe, list of dicts or list
# of ORM objects. See 'fmt' option.
#
#
# jobids : Optional list of jobids to narrow the search space
#
# tags   : Optional dictionary or string of key/value pairs
#
# fltr   : Optional filter in the form of a lamdba function or a string
#          e.g., lambda j: count(j.processes) > 100 will filter jobs more than 100 processes
#          or, 'j.duration > 100000' will filter jobs whose duration is more than 100000
#
# order  : Optionally sort the output by setting this to a lambda function or string
#          e.g, to sort by job duration descending:
#               order = 'desc(j.duration)'
#          or, to sort jobs by the sum of durations of their processes, do:
#               order = lambda j: sum(j.processes.duration)
#
# limit  : Restrict the output list a specified number of jobs
#
# fmt    : Control the output format. One of 'dict', 'pandas', 'orm', 'terse'
#          'dict': each job object is converted to a dict, and the entire
#                  output is a list of dictionaries
#          'pandas': Output a pandas dataframe with one row for each matching job
#          'orm':  returns a Pony Query object (ADVANCED)
#          'terse': In this format only the primary key ID is printed for each job
#
# merge_proc_sums: By default True, which means the fields inside job.proc_sums
#          will be hoisted up one level to become first-class members of the job.
#          This will make aggregates across processes appear as part of the job
#          If False, the job will contain job.proc_sums, which will be a dict
#          of key/value pairs, where each is an process attribute, such as numtids,
#          and the value is the sum acorss all processes of the job.
#
# exact_tags_only: If set, tags will be considered matched if saved tags have
#          to identically match the passed tags. The default is False, which
#          means if the tags in the database are a superset of the passed
#          tags a match will considered.
#
# sql_debug: Show SQL queries, default False
#              
#
def get_jobs(jobids = [], tags={}, fltr = '', order = '', limit = 0, fmt='dict', merge_proc_sums=True, exact_tags_only = False, sql_debug = False):
    set_sql_debug(sql_debug)
    if jobids:
        if (type(jobids) == str) or (type(jobids) == unicode):
            # user either gave the job id directly instead of passing a list
            jobids = jobids.split(',')
        qs = Job.select(lambda j: j.jobid in jobids)
    else:
        qs = Job.select()

    # filter using tags if set
    if type(tags) == str:
        tags = get_tags_from_string(tags)
    if exact_tags_only:
        qs = qs.filter(lambda j: j.tags == tags)
    else:
        # we consider a match if the job tags are a superset
        # of the passed tags
        for (k,v) in tags.items():
            qs = qs.filter(lambda j: j.tags[k] == v)

    # if fltr is a lambda function or a string apply it
    if fltr:
        qs = qs.filter(fltr)

    if order:
        qs = qs.order_by(order)

    # finally set limits on the number of jobs returned
    if limit:
        qs = qs.limit(int(limit))

    if fmt == 'orm':
        return qs

    if fmt == 'terse':
        return [ j.jobid for j in qs ]

    # convert the ORM into a list of dictionaries, excluding blacklisted fields
    exclude_fields = (settings.query_job_fields_exclude or '') if hasattr(settings, 'query_job_fields_exclude') else ''
    out_list = [ j.to_dict(exclude = exclude_fields) for j in qs ]

    # do we need to merge threads' sum fields into the process?
    if merge_proc_sums:
        for j in out_list:
            j.update(j[settings.proc_sums_field_in_job])
            del j[settings.proc_sums_field_in_job]

    if fmt == 'pandas':
        return pd.DataFrame(out_list)

    # we assume the user wants the output in the form of a list of dicts
    return out_list

# Filter a supplied list of jobs to find a match
# by tags or some primary keys. If no jobs list is provided,
# then the query will be run against all processes.
#
# All fields are optional and sensible defaults are assumed.
#
# tags : is a dictionary or string of key/value pairs and is optional.
#
# fltr: is a lambda expression or a string of the form:
#       lambda p: p.duration > 1000
#        OR
#       'p.duration > 1000 and p.numtids < 4'
#
# limit: if set, limits the total number of results
# 
# fmt :   Output format, is one of 'dict', 'orm', 'pandas', 'terse'
#         'dict': This is the default, and in this case
#                 each process is output as a python dictionary, 
#                 and the entire output is a list of dictionaries.
#         'pandas': output is a pandas dataframe
#         'orm': output is an ORM Query object (ADVANCED)
#         'terse': output contains only the database ids of matching processes
#
# merge_threads_sums: By default, this is True, and this means threads sums are
#          are folded into the process. If set to False, the threads'
#          sums will be available as a separate field settings.thread_sums_field_in_proc.
#          Flattening makes subsequent processing easier as all the
#          thread aggregates such as 'usertime', 'systemtime' are available
#          as first-class members of the process. This option is silently
#          ignored if output format 'fmt' is set to 'orm', and ORM
#          objects will not be merge_threads_sumsed.
#
# exact_tags_only: If set, tags will be considered matched if saved tags have
#          to identically match the passed tags. The default is False, which
#          means if the tags in the database are a superset of the passed
#          tags a match will considered.
#
# sql_debug: Show/hide SQL queries. Default False.
#
# For example, to get all processes for a particular Job, with jobid '32046', which
# are multithreaded, you would do:
#
#   get_procs(jobs = ['32046'], fltr = 'p.numtids > 1')
#
# To filter all processes that have tags = {'app': 'fft'}, you would do:
# get_procs(tags = {'app': 'fft'})
#
# to get a pandas dataframe:
# qs1 = get_procs(tags = {'app': 'fft'}, fmt = 'pandas')
#
# to filter processes for a job '1234' and order by process duration,
# getting the top 10 results, and keeping the final output in ORM format:
# 
# q = get_procs(['1234'], order = 'desc(p.duration)', limit=10, fmt='orm')
#
# now, let's filter processes with duration > 100000 and order them by user+system time,
# and let's get the output into a pandas dataframe:
# q = get_procs(fltr = (lambda p: p.duration > 100000), order = 'desc(p.threads_sums["user+system"]', fmt='pandas')
# Observe, that while 'user+system' is a metric available in the threads_sums field,
# by using the default merge_threads_sums=True, it will be available as column in the output
# dataframe. The output will be pre-sorted on this field because we have set 'order'
#
def get_procs(jobs = [], tags = {}, fltr = None, order = '', limit = 0, fmt='dict', merge_threads_sums=True, exact_tags_only = False, sql_debug = False):
    set_sql_debug(sql_debug)
    if jobs:
        if isinstance(jobs, Query):
            # convert the pony query object to a list
            jobs = jobs[:]

        if type(jobs) != list:
            # user probably passed a single job, and forgot to wrap it in a list
            jobs = [jobs]
        # is jobs a collection of Job IDs or actual Job objects?
        if type(jobs[0]) == str or type(jobs[0]) == unicode:
            # jobs is a list of job IDs
            qs = Process.select(lambda p: p.job.jobid in jobs)
        else:
            # jobs is a list of Job objects
            qs = Process.select(lambda p: p.job in jobs)
    else:
        # no jobs set, so expand the scope to all Process objects
        qs = Process.select()

    # filter using tags if set
    if type(tags) == str:
        tags = get_tags_from_string(tags)
    if exact_tags_only:
        qs = qs.filter(lambda p: p.tags == tags)
    else:
        # we consider a match if the job tags are a superset
        # of the passed tags
        for (k,v) in tags.items():
            qs = qs.filter(lambda p: p.tags[k] == v)

    # if fltr is a lambda function or a string apply it
    if fltr:
        qs = qs.filter(fltr)

    if order:
        qs = qs.order_by(order)

    # finally set limits on the number of processes returned
    if limit:
        qs = qs.limit(int(limit))

    if fmt == 'orm':
        return qs

    if fmt == 'terse':
        return [ p.id for p in qs ]

    # convert the ORM into a list of dictionaries, excluding blacklisted fields
    proc_exclude_fields = (settings.query_process_fields_exclude or '') if hasattr(settings, 'query_process_fields_exclude') else ''
    out_list = [ p.to_dict(exclude = proc_exclude_fields) for p in qs ]

    # do we need to merge threads' sum fields into the process?
    if merge_threads_sums:
        for p in out_list:
            p.update(p[settings.thread_sums_field_in_proc])
            del p[settings.thread_sums_field_in_proc]

    if fmt == 'pandas':
        return pd.DataFrame(out_list)

    # we assume the user wants the output in the form of a list of dicts
    return out_list


# returns thread metrics dataframe for one or more processes
# where each process is specified as either as a Process object or 
# the database ID of a process.
# If multiple processes are specified then dataframes are concatenated
# using pandas into a single dataframe
def get_thread_metrics(*processes):
    # handle the case where the user supplied a python list rather
    # spread out arguments
    if type(processes[0]) == list:
        processes = processes[0]

    df_list = []
    for proc in processes:
        if type(proc) == int:
            # user supplied database id of process
            p = Process.select(lambda p: p.id == proc).first()
        else:
            # user supplied process objects directly
            p = proc
        df = pd.read_json(p.threads_df, orient='split')
        # add a synthetic column set to the primary key of the process
        df['process_pk'] = p.id

        df_list.append(df)

    # if we have only one dataframe then no concatenation is needed
    return pd.concat(df_list) if len(df_list) > 1 else df_list[0]


# gets all the unique tags across all processes of a job or list of jobs
# jobs: is a single job id or a Job object, or a list of jobids/list of job objects
# If 'fold' is set, then tags will be merged to compact the output
# otherwise, the expanded list of dictionaries is returned
# 'exclude' is an optional list of keys to exclude from each tag (if present)
def get_unique_process_tags(jobs = [], exclude=[], fold=True):
    if jobs:
        if isinstance(jobs, Query):
            # convert the pony query object to a list
            jobs = list(jobs[:])
    else:
        # all Jobs
        jobs = list(Job.select()[:])

    if type(jobs) != list:
        # wrap jobs into a list. It's either a string jobid or Job object
        jobs = [jobs]

    # at this point jobs is a list of job ids or Job objects
    # let's make sure it's a list of Job objects
    jobs = [ Job[j] if (type(j) == str or type(j) == unicode) else j for j in jobs ]
    tags = []
    for j in jobs:
        unique_tags_for_job = _get_unique_process_tags_for_single_job(j, exclude, fold = False)
        tags.extend(unique_tags_for_job)
    # remove duplicates
    tags = unique_dicts(tags, exclude)
    return fold_dicts(tags) if fold else tags


# This is a low-level function that finds the unique process
# tags for a job (job is either a job id or a Job object). 
# See also: get_unique_process_tags, which does the same
# for a list of jobs
def _get_unique_process_tags_for_single_job(job, exclude=[], fold=True):
    if type(job) == str or type(job) == unicode:
        job = Job[job]
    proc_sums = getattr(job, settings.proc_sums_field_in_job, {})
    tags = []
    if proc_sums:
        tags = proc_sums[settings.all_tags_field]
    else:
        # if we haven't found it the easy way, do the heavy compute
        import numpy as np
        tags = np.unique(np.array(job.processes.tags)).tolist()

    # get unique dicts after removing exclude keys
    if exclude:
        tags = unique_dicts(tags, exclude)

    return fold_dicts(tags) if fold else tags


# returns a list of dicts (or dataframe), each row is of the form:
# <job-id>,<tag>, metric1, metric2, etc..
# You pass as argument a job or a list of jobs, and
# tags is passed in as a list of strings or dictionaries. You
# may optionally pass a single tag as a string or dict.
# If exatct_tags_only is set (default False), then a match
# means there is an exact match of the tag dictionaries
# In this function, fmt is only allowed 'pandas' or 'dict'
#
def agg_metrics_by_tags(jobs = [], tags = [], exact_tags_only = False, fmt='pandas', sql_debug = False):
    set_sql_debug(sql_debug)

    if type(jobs) == str or type(jobs) == unicode:
        jobs = [jobs]

    if not tags:
       if (len(jobs) > 1):
           print("You must specify tags as non-empty string or dictionary", stderr)
           return None
       # as we have only a single job, let's figure out all the
       # tags for the job
       tags = get_all_tags_in_job(jobs[0], fold=False)

    # do we have a single tag in string or dict form? 
    if type(tags) == str:
        tags = [get_tags_from_string(tags)]
    elif type(tags) == dict:
        tags = [tags]

    all_procs = []
    # we iterate over tags, where each tag is dictionary
    for t in tags:
        procs = get_procs(jobs, tags = t, exact_tags_only = exact_tags_only, sql_debug = sql_debug, fmt='orm')
        # group the Query response we got by jobid
        # we use group_concat to join the thread_sums json into a giant string
        procs_grp_by_job = select((p.job, count(p.id), sum(p.duration), sum(p.exclusive_cpu_time), sum(p.numtids), group_concat(p.threads_sums, sep='@@@')) for p in procs)
        for row in procs_grp_by_job:
            (j, nprocs, duration, excl_cpu, ntids, threads_sums_str) = row
            # convert from giant string to array of strings where each list
            # list element is a json of a threads_sums dict
            _l1 = threads_sums_str.split('@@@')
            # get back the dicts
            thr_sums_dicts = [loads(s) for s in _l1]
            # now aggregate across the dicts
            sum_dict = {}
            for d in thr_sums_dicts:
                sum_dict = _sum_dicts(sum_dict, d)
            # add some useful fields so we can back-reference and
            # also add some sums we obtained in the query
            sum_dict.update({'job': j.jobid, 'tags': t, 'num_procs': nprocs, 'num_tids': ntids, 'exclusive_cpu_time': excl_cpu, 'duration': duration})
            all_procs.append(sum_dict)

    if fmt == 'pandas':
        return pd.DataFrame(all_procs)

    # we assume the user wants the output in the form of a list of dicts
    return all_procs
