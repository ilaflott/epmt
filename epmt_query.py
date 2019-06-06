from models import *
from epmt_job import setup_orm_db
import pandas as pd
from pony.orm.core import Query
import settings
print(settings.db_params)
setup_orm_db(settings)


THR_SUMS_FIELD = 'threads_sums'

# This function returns a list of jobs based on some filtering and ordering.
# The output format can be set to pandas dataframe, list of dicts or list
# of ORM objects. See 'fmt' option.
#
#
# jobids : Optional list of jobids to narrow the search space
#
# tags   : Optional dictionary of key/value pairs
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
def get_jobs(jobids = [], tags={}, fltr = '', order = '', limit = 0, fmt='dict'):
    if jobids:
        if (type(jobids) == str) or (type(jobid) == unicode):
            # user either gave the job id directly instead of passing a list
            jobids = jobids.split(',')
        qs = Job.select(lambda j: j.jobid in jobids)
    else:
        qs = Job.select()

    # filter using tags if set
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
# tags : is a dictionary of key/value pairs and is optional.
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
#          sums will be available as a separate field THR_SUMS_FIELD.
#          Flattening makes subsequent processing easier as all the
#          thread aggregates such as 'usertime', 'systemtime' are available
#          as first-class members of the process. This option is silently
#          ignored if output format 'fmt' is set to 'orm', and ORM
#          objects will not be merge_threads_sumsed.
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
def get_procs(jobs = [], tags = {}, fltr = None, order = '', limit = 0, fmt='dict', merge_threads_sums=True):
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
            p.update(p[THR_SUMS_FIELD])
            del p[THR_SUMS_FIELD]

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
        df_list.append(pd.read_json(p.threads_df, orient='split'))

    # if we have only one dataframe then no concatenation is needed
    return pd.concat(df_list) if len(df_list) > 1 else df_list[0]
