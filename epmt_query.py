from __future__ import print_function
from sys import stderr
from datetime import datetime
import pandas as pd
from pony.orm.core import Query, QueryResult
from pony.orm import *
from json import loads, dumps
from os import environ
from logging import getLogger
from models import Job, Process, ReferenceModel, Host
from epmtlib import tag_from_string, tags_list, set_logging, init_settings, sum_dicts, unique_dicts, fold_dicts, isString
from epmt_stat import modified_z_score

logger = getLogger(__name__)  # you can use other name
set_logging(0, check=True)

# put epmt imports after this test
if environ.get('EPMT_USE_DEFAULT_SETTINGS'):
    logger.warning('ignoring settings.py and using defaults in epmt_default_settings')
    import epmt_default_settings as settings
else:
    import settings
from epmt_job import setup_orm_db



init_settings(settings)
setup_orm_db(settings)

PROC_SUMS_FIELD_IN_JOB='proc_sums'
THREAD_SUMS_FIELD_IN_PROC='threads_sums'

# figure out the entity type and then call the appropriate 
# convertor. For now we know its either a collection of Job or Process objects
# def conv_orm(entities, merge_sub_sums=True, fmt='dict'):
#     e1 = entities[0] if type(entities) == list else entities.first()
#     return conv_jobs(entities, merge_sub_sums, fmt) if e1.__class__.__name__ == 'Job' else conv_procs_orm(entities, merge_sub_sums, fmt)


# jobs is a jobs collection (Pony) or a list of Job objects,
# or a list of jobids, or a pandas dataframe or a dictlist of jobs.
# 'merge_sums' is silently ignored for fmt 'orm' or 'terse'
def conv_jobs(jobs, fmt='dict', merge_sums = True):
    jobs = __jobs_col(jobs)
    if fmt == 'orm':
        return jobs
    if fmt=='terse':
        return [ j.jobid for j in jobs ]

    # convert the ORM into a list of dictionaries, excluding blacklisted fields
    out_list = [ j.to_dict() for j in jobs ]

    # do we need to merge threads' sum fields into the process?
    if merge_sums:
        for j in out_list:
            # check if dicts have any common fields, if so,
            # warn the user as some fields will get clobbered
            common_fields = list(set(j) & set(j[PROC_SUMS_FIELD_IN_JOB]))
            if common_fields:
                logger.warning('while hoisting proc_sums to job-level, found {0} common fields: {1}'.format(len(common_fields), common_fields))
            j.update(j[PROC_SUMS_FIELD_IN_JOB])
            del j[PROC_SUMS_FIELD_IN_JOB]

    return pd.DataFrame(out_list) if fmt=='pandas' else out_list


# procs is an ORM Query object on Process or a list of Process objects
def conv_procs_orm(procs, merge_sums = True, fmt='dict'):
    if fmt=='terse':
        return [ p.id for p in procs ]

    # convert the ORM into a list of dictionaries, excluding blacklisted fields
    out_list = [ p.to_dict(exclude = 'threads_df') for p in procs ]

    # do we need to merge threads' sum fields into the process?
    if merge_sums:
        for p in out_list:
            # check if dicts have any common fields, if so,
            # warn the user as some fields will get clobbered
            common_fields = list(set(p) & set(p[THREAD_SUMS_FIELD_IN_PROC]))
            if common_fields:
                logger.warning('while hoisting thread_sums to process-level, found {0} common fields: {1}'.format(len(common_fields), common_fields))
            p.update(p[THREAD_SUMS_FIELD_IN_PROC])
            # add an alias for a consistent user experience
            p['jobid'] = p['job']
            del p[THREAD_SUMS_FIELD_IN_PROC]
    return pd.DataFrame(out_list) if fmt == 'pandas' else out_list

# this is an internal function to take a collection of jobs
# in a variety of formats and return output in a specified format
# You should not use this function directly, but instead use
# conv_jobs()
def __jobs_col(jobs):
    if type(jobs) in [Query, QueryResult]:
        return jobs
    if ((type(jobs) != pd.DataFrame) and not(jobs)):
        return Job.select()
    if type(jobs) == pd.DataFrame:
        jobs = list(jobs['jobid'])
    if isString(jobs):
        if ',' in jobs:
            # jobs a string of comma-separated job ids
            jobs = [ j.strip() for j in jobs.split(",") ]
        else:
            # job is a single jobid
            jobs = Job[jobs]
    if type(jobs) == Job:
        # is it a singular job?
        jobs = [jobs]
    if type(jobs) in [list, set]:
        # jobs is a list of Job objects or a list of jobids or a list of dicts
        # so first convert the dict list to a jobid list
        jobs = [ j['jobid'] if type(j) == dict else j for j in jobs ]
        jobs = [ Job[j] if isString(j) else j for j in jobs ]
        # and now convert to a pony Query object so the user can chain
        jobs = Job.select(lambda j: j in jobs)
    return jobs


# this function returns a timeline of processes
# ordered chronologically by start time.
# jobs is either a collection of jobs or a single job, where 
# jobs can be specified as jobids or Job objects.
# 
# The function takes the same arguments as get_procs is a very
# slim wrapper over it, just setting an ordering by start time.
#
# >>> eq.timeline([u'685000', u'685016'], limit=5)[['job', 'exename', 'start', 'id']]
#       job    exename                      start    id
# 0  685000       tcsh 2019-06-15 11:52:04.126892  3413
# 1  685000       tcsh 2019-06-15 11:52:04.133795  3414
# 2  685000      mkdir 2019-06-15 11:52:04.142141  3415
# 3  685000  modulecmd 2019-06-15 11:52:04.176020  3416
# 4  685000       test 2019-06-15 11:52:04.192758  3417
#
# >>> eq.timeline([u'685000', u'685016'], limit=5, hosts=[Host[u'pp313'], Host[u'pp208']])[['job', 'exename', 'start', 'host']]
#       job    exename                      start   host
# 0  685000       tcsh 2019-06-15 11:52:04.126892  pp208
# 1  685000       tcsh 2019-06-15 11:52:04.133795  pp208
# 2  685000      mkdir 2019-06-15 11:52:04.142141  pp208
# 3  685000  modulecmd 2019-06-15 11:52:04.176020  pp208
# 4  685000       test 2019-06-15 11:52:04.192758  pp208
#
def timeline(jobs = [], limit=0, fltr='', when=None, hosts=[], fmt='pandas'):
    return get_procs(jobs, fmt=fmt, order='p.start', limit=limit, fltr=fltr, when=when, hosts=hosts)

#
# get the root process of the job
# The job is either a Job object or a jobid
#
# EXAMPLE:
# >>> eq.root('685016',fmt='terse')
# 7266
#
# >>> p = eq.root('685016',fmt='orm')
# >>> p.id
# 7266
# >>> p.exename
# u'tcsh'
# >>> p.args
# u'-f /home/Jeffrey.Durachta/ESM4/DECK/ESM4_historical_D151/gfdl.ncrc4-intel16-prod-openmp/scripts/postProcess/ESM4_historical_D151_ocean_month_rho2_1x1deg_18840101.tags'
# >>> p.descendants.count()
# 3381
#
# >>> df = eq.root('685016', fmt='pandas')
# >>> df.shape
# (1,49)
# >>> df.loc[0,'pid']
# 122181
#
# >>> p = eq.root('685016')
# >>> p['id'],p['exename']
# (7266, u'tcsh')
@db_session
def root(job, fmt='dict'):
    if isString(job):
        job = Job[job]
    p = job.processes.order_by('p.start').limit(1)
    if fmt == 'orm': return p.to_list().pop()
    if fmt == 'terse': return p.to_list().pop().id

    plist = conv_procs_orm(p, fmt='dict')
    return pd.DataFrame(plist) if fmt == 'pandas' else plist.pop()

# This function returns a list of jobs based on some filtering and ordering.
# The output format can be set to pandas dataframe, list of dicts or list
# of ORM objects. See 'fmt' option.
#
#
# jobs   : Optional list of jobs to narrow the search space. The jobs can
#          a list of jobids (i.e., list of strings), or the result of a Pony
#          query on Job (i.e., a Query object), or a pandas dataframe of jobs
#          
#
# tag    : Optional dictionary or string of key/value pairs. If set to ''
#          or {], then exact_tag_match will be implicitly set, and only
#          those jobs that have an empty tag will match. 
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
#          If not set, this defaults to desc(j.created_at), in other words
#          jobs are returned in the reverse order of ingestion.
#
# limit  : Restrict the output list a specified number of jobs. Defaults to 20.
#          When set to 0, it means no limit
#
# when   : Restrict the output to jobs running at 'when' time. 'when'
#          can be specified as a Python datetime. You can also choose
#          to specify 'when' as jobid or a Job object. In which 
#          case the output will be restricted to those jobs that 
#          had an overlap with the specified 'when' job. 
#
# hosts  : Restrict the output to those jobs that ran on 'hosts'.
#          'hosts' is a list of hostnames/Host objects. A job is
#          consider to match if the intersection of j.hosts and hosts is non-empty
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
# exact_tag_only: If set, tag will be considered matched if saved tag
#          identically matches the passed tag. The default is False, which
#          means if the tag in the database are a superset of the passed
#          tag a match will considered.
#
#
@db_session
def get_jobs(jobs = [], tag=None, fltr = '', order = None, limit = None, when=None, hosts=[], fmt='dict', merge_proc_sums=True, exact_tag_only = False):

    # set defaults for limit and ordering only if the user doesn't specify jobs
    if jobs in [[], '', None]:
        if limit == None: limit = 20
        if order == None: order = 'desc(j.created_at)'
      
    qs = __jobs_col(jobs)

    # filter using tag if set
    # Remember, tag = {} demands an exact match with an empty dict!
    if tag != None:
        if type(tag) == str:
            tag = tag_from_string(tag)
        if exact_tag_only or (tag == {}):
            qs = qs.filter(lambda j: j.tags == tag)
        else:
            # we consider a match if the job tag is a superset
            # of the passed tag
            for (k,v) in tag.items():
                qs = qs.filter(lambda j: j.tags[k] == v)

    # if fltr is a lambda function or a string apply it
    if fltr:
        qs = qs.filter(fltr)

    if when:
        if type(when) == datetime:
            qs = qs.filter(lambda j: j.start <= when and j.end >= when)
        else:
            when_job = Job[when] if isString(when) else when
            qs = qs.filter(lambda j: j.start <= when_job.end and j.end >= when_job.start)

    if hosts:
        if isString(hosts) or (type(hosts) == Host):
            # user probably forgot to wrap in a list
            hosts = [hosts]
        if type(hosts) == list:
            # if the list contains of strings then we want the Host objects
            hosts = [Host[h] if isString(h) else h for h in hosts]
        qs = select(j for j in qs for h in j.hosts if h in hosts)

    if order:
        qs = qs.order_by(order)

    # finally set limits on the number of jobs returned
    if limit:
        qs = qs.limit(int(limit))

    if fmt == 'orm':
        return qs

    return conv_jobs(qs, fmt, merge_proc_sums)


# Filter a supplied list of jobs to find a match
# by tag or some primary keys. If no jobs list is provided,
# then the query will be run against all processes.
#
# All fields are optional and sensible defaults are assumed.
#
# tag : is a dictionary or string of key/value pairs and is optional.
#       If set to '' or {}, exact_tag_match will be implicitly
#       set, and only those processes with an empty tag will match.
#
# fltr: is a lambda expression or a string of the form:
#       lambda p: p.duration > 1000
#        OR
#       'p.duration > 1000 and p.numtids < 4'
#
# limit: if set, limits the total number of results
# 
# when   : Restrict the output to processes running at 'when' time. 'when'
#          can be specified as a Python datetime. You can also choose
#          to specify 'when' as process PK or a Process object. In which 
#          case the output will be restricted to those processes that 
#          had an overlap with the specified 'when' process. 
#
# hosts  : Restrict the output to those processes that ran on 'hosts'.
#          'hosts' is a list of hostnames/Host objects. A process is
#          consider to match if process.host is in the list of 'hosts'
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
#          sums will be available as a separate field THREAD_SUMS_FIELD_IN_PROC.
#          Flattening makes subsequent processing easier as all the
#          thread aggregates such as 'usertime', 'systemtime' are available
#          as first-class members of the process. This option is silently
#          ignored if output format 'fmt' is set to 'orm', and ORM
#          objects will not be merge_threads_sumsed.
#
# exact_tag_only: If set, tag will be considered matched if saved tag
#          identically matches the passed tag. The default is False, which
#          means if the tag in the database are a superset of the passed
#          tag a match will considered.
#
# For example, to get all processes for a particular Job, with jobid '32046', which
# are multithreaded, you would do:
#
#   get_procs(jobs = ['32046'], fltr = 'p.numtids > 1')
#
# To filter all processes that have tag = {'app': 'fft'}, you would do:
# get_procs(tag = {'app': 'fft'})
#
# to get a pandas dataframe:
# qs1 = get_procs(tag = {'app': 'fft'}, fmt = 'pandas')
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
@db_session
def get_procs(jobs = [], tag = None, fltr = None, order = '', limit = 0, when=None, hosts=[], fmt='dict', merge_threads_sums=True, exact_tag_only = False):
    if jobs:
        jobs = __jobs_col(jobs)
        qs = Process.select(lambda p: p.job in jobs)
    else:
        # no jobs set, so expand the scope to all Process objects
        qs = Process.select()

    # filter using tag if set
    # Remember, tag = {} demands an exact match with an empty dict!
    if tag != None:
        if type(tag) == str:
            tag = tag_from_string(tag)
        if exact_tag_only or (tag == {}):
            qs = qs.filter(lambda p: p.tags == tag)
        else:
            # we consider a match if the job tag is a superset
            # of the passed tag
            for (k,v) in tag.items():
                qs = qs.filter(lambda p: p.tags[k] == v)

    # if fltr is a lambda function or a string apply it
    if fltr:
        qs = qs.filter(fltr)

    if when:
        if type(when) == datetime:
            qs = qs.filter(lambda p: p.start <= when and p.end >= when)
        else:
            when_process = Process[when] if isString(when) else when
            qs = qs.filter(lambda p: p.start <= when_process.end and p.end >= when_process.start)

    if hosts:
        if isString(hosts) or (type(hosts) == Host):
            # user probably forgot to wrap in a list
            hosts = [hosts]
        if type(hosts) == list:
            # if the list contains of strings then we want the Host objects
            hosts = [Host[h] if isString(h) else h for h in hosts]
        qs = qs.filter(lambda p: p.host in hosts)

    if order:
        qs = qs.order_by(order)

    # finally set limits on the number of processes returned
    if limit:
        qs = qs.limit(int(limit))

    if fmt == 'orm':
        return qs

    return conv_procs_orm(qs, merge_threads_sums, fmt)



# Returns:
# thread metrics dataframe for one or more processes
# None if error
# where each process is specified as either as a Process object or 
# the database ID of a process.
# If multiple processes are specified then dataframes are concatenated
# using pandas into a single dataframe
@db_session
def get_thread_metrics(*processes):
    # handle the case where the user supplied a python list rather
    # spread out arguments
    if type(processes[0]) == list:
        processes = processes[0]
    if len(processes) == 0:
        logger.warning("get_thread_metrics must be given one or more Process objects or primary keys")
        return pd.DataFrame()

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
@db_session
def get_job_proc_tags(jobs = [], exclude=[], fold=False):
    return(job_proc_tags(jobs=jobs,exclude=exclude,fold=fold))

@db_session
def job_proc_tags(jobs = [], exclude=[], fold=False):
    jobs = __jobs_col(jobs)
    tags = []
    for j in jobs:
        unique_tags_for_job = __unique_proc_tags_for_job(j, exclude, fold = False)
        tags.extend(unique_tags_for_job)
    # remove duplicates
    tags = unique_dicts(tags, exclude)
    return fold_dicts(tags) if fold else tags


# This function returns reference models filtered using tag and fltr
# tag refers to a single dict of key/value pairs or a string
# fltr is a lambda function or a string containing a pony expression
# limit is used to limit the number of output items, 0 means no limit
# order is used to order the output list, its a lambda function or a string
# exact_tag_only is used to match the DB tag with the supplied tag:
#   the full dictionary must match for a successful match. Default False.
# merge_nested_fields is used to hoist attributes from the 'computed'
#   fields in the reference model, so they appear as first-class fields.
# fmt is one of 'orm', 'pandas', 'dict'. Default is 'dict'
# example usage:
#   get_refmodels(tag = 'exp_name:ESM4;exp_component:ice_1x1', fmt='pandas')
#
@db_session
def get_refmodels(tag = {}, fltr=None, limit=0, order='', exact_tag_only=False, merge_nested_fields=True, fmt='dict'):
    qs = ReferenceModel.select()

    # filter using tag if set
    if type(tag) == str:
        tag = tag_from_string(tag)
    if exact_tag_only:
        qs = qs.filter(lambda r: r.tags == tag)
    else:
        # we consider a match if the job tags are a superset
        # of the passed tags
        for (k,v) in tag.items():
            qs = qs.filter(lambda r: r.tags[k] == v)

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
        return [ r.id for r in qs ]
    
    out_list = [ r.to_dict(with_collections=True) for r in qs ]

    # do we need to merge nested fields?
    if merge_nested_fields:
        for r in out_list:
            # check if dicts have any common fields, if so,
            # warn the user as some fields will get clobbered
            common_fields = list(set(r) & set(r['computed']))
            if common_fields:
                logger.warning('while hoisting nested fields in "computed" to reference model, found {0} common fields: {1}'.format(len(common_fields), common_fields))
            r.update(r['computed'])
            del r['computed']

    if fmt == 'pandas':
        return pd.DataFrame(out_list)

    # we assume the user wants the output in the form of a list of dicts
    return out_list


# This function computes a dict such as:
# { 'z_score': {'duration': (max, median, median_dev), {'cpu_time': (max, median, median_dev)},
#   'iqr': {'duration': ...}
#
# col: is either a dataframe or a collection of jobs (Query/list of Job objects)
def _refmodel_scores(col, outlier_methods, features):
    df = conv_jobs(col, fmt='pandas') if col.__class__.__name__ != 'DataFrame' else col
    ret = {}
    for m in outlier_methods:
        ret[m.__name__] = {}
        for c in features:
            # we save everything except the first element of the
            # tuple as the first element is the actual scores
            ret[m.__name__][c] = m(df[c])[1:]
    return ret
#
# This function creates a reference model and returns
# the ID of the newly-created model in the database
# 
#
# jobs:     points to a list of Jobs (or pony JobSet) or jobids
#
# tag:      A string or dict consisting of key/value pairs. This
#           tag is saved for the refmodel, and may be used
#           in a filter while retrieving the refmodel.
#
# op_tags:  A list of strings or dicts. This is optional,
#           if set, it will restrict the model to the filtered ops.
#           op_tags are distinct from "tag". op_tags are used to
#           obtain the set of processes over which an aggregation
#           is performed using op_metrics. 
#
# outlier_methods: Is a list of methods that are used to obtain
#          scores. Each method is passed a vector consisting
#          of the value of 'feature' for all the jobs. The
#          method will return a vector of scores. This
#          vector of scores will be saved (or some processed
#          form of it). If methods is not specified then it
#          will at present be set to modified_z_score.
#
# features: List of fields of each job that should be used
#          for outlier detection. 
#          Defaults to: ['duration', 'cpu_time', 'num_procs']
#
# exact_tag_only: Default False. If set, all tag matches require
#          exact dictionary match, and a superset match won't do.
#
# e.g,.
#
# create a job ref model with a list of jobids
# eq.create_refmodel(jobs=[u'615503', u'625135'])
#
# or use pony orm query result:
# >>> jobs = eq.get_jobs(tag='exp_component:atmos', fmt='orm')
# >>> r = eq.create_refmodel(jobs)
#
# to create a refmodel for ops we need to either set op_tags
# to a list of tags for the ops, or use the wildcard (*):
# >>> r = eq.create_refmodel(jobs, tag='exp_name:linux_kernel', op_tags='*')
#
# >>> r['id'], r['tags'], r['jobs']
# (11, {'exp_name': 'linux_kernel'}, [u'kern-6656-20190614-190245', u'kern-6656-20190614-191138', u'kern-6656-20190614-192044-outlier', u'kern-6656-20190614-194024'])
#
# >>> r['op_tags']
# [{u'op_instance': u'4', u'op_sequence': u'4', u'op': u'build'}, {u'op_instance': u'5', u'op_sequence': u'5', u'op': u'clean'}, {u'op_instance': u'3', u'op_sequence': u'3', u'op': u'configure'}, {u'op_instance': u'1', u'op_sequence': u'1', u'op': u'download'}, {u'op_instance': u'2', u'op_sequence': u'2', u'op': u'extract'}]

#
#
@db_session
def create_refmodel(jobs=[], tag={}, op_tags=[], 
                    outlier_methods=[modified_z_score], 
                    features=['duration', 'cpu_time', 'num_procs'], exact_tag_only=False,
                    fmt='dict'):
    if (not jobs) or len(jobs)==0:
        logger.error('You need to specify one or more jobs to create a reference model')
        return None

    if type(tag) == str:
        tag = tag_from_string(tag)

    # do we have a list of jobids?
    # if so, we need to get the actual DB objects for them
    if type(jobs) == set:
        jobs = list(jobs)
    if type(jobs) == list and isString(jobs[0]):
        jobs = Job.select(lambda j: j.jobid in jobs)

    if op_tags:
        if op_tags == '*':
            logger.info('wildcard op_tags set: obtaining set of unique tags across the input jobs')
            op_tags = job_proc_tags(jobs, fold=False)
        # do we have a single tag in string or dict form? 
        # we eventually want a list of dicts
        elif type(op_tags) == str:
            op_tags = [tag_from_string(op_tags)]
        elif type(op_tags) == dict:
            op_tags = [op_tags]
        # let's get the dataframe of metrics aggregated by op_tags
        ops_df = get_op_metrics(jobs = jobs, tags = op_tags, exact_tags_only = exact_tag_only, fmt='pandas')
        scores = {}
        for t in op_tags:
            # serialize the tag so we can use it as a key
            stag = dumps(t, sort_keys=True)
            scores[stag] = _refmodel_scores(ops_df[ops_df.tags == t], outlier_methods, features)
    else:
        # full jobs, no ops
        scores = _refmodel_scores(jobs, outlier_methods, features)

    logger.debug('computed scores: {0}'.format(scores))
    computed = scores

    # now save the ref model
    r = ReferenceModel(jobs=jobs, tags=tag, op_tags=op_tags, computed=computed)
    commit()
    if fmt=='orm': 
        return r
    elif fmt=='terse': 
        return r.id
    r_dict = r.to_dict(with_collections=True)
    return pd.Series(r_dict) if fmt=='pandas' else r_dict

            
# This is a low-level function that finds the unique process
# tags for a job (job is either a job id or a Job object). 
# See also: job_proc_tags, which does the same
# for a list of jobs
def __unique_proc_tags_for_job(job, exclude=[], fold=True):
    global settings
    if isString(job):
        job = Job[job]
    proc_sums = getattr(job, PROC_SUMS_FIELD_IN_JOB, {})
    tags = []
    try:
        tags = proc_sums[settings.all_tags_field]
    except:
        # if we haven't found it the easy way, do the heavy compute
        import numpy as np
        tags = np.unique(np.array(job.processes.tags)).tolist()

    # get unique dicts after removing exclude keys
    if exclude:
        tags = unique_dicts(tags, exclude)

    return fold_dicts(tags) if fold else tags

# Notebook compat function
@db_session
def op_metrics(jobs = [], tags = [], exact_tags_only = False, fmt='pandas'):
    return get_op_metrics(jobs,tags,exact_tags_only,fmt)

# returns a list of dicts (or dataframe), each row is of the form:
# <job-id>,<tag>, metric1, metric2, etc..
# You pass as argument a job or a list of jobs, and
# tags is passed in as a list of strings or dictionaries. You
# may optionally pass a single tag as a string or dict.
# If exatct_tags_only is set (default False), then a match
# means there is an exact match of the tag dictionaries.
# If no tags are passed, then the set of unique tags for the jobs
# will be used.
# In this function, fmt is only allowed 'pandas' or 'dict'
#
@db_session
def get_op_metrics(jobs = [], tags = [], exact_tags_only = False, fmt='pandas'):
    if not jobs:
        logger.warning('You need to specify one or more jobs for op_metrics')
        return None

    if isString(jobs):
        jobs = [jobs]

    tags = tags_list(tags) if tags else job_proc_tags(jobs, fold=False)
    if not tags:
        logger.warning('No tags found across all processes of job(s)')
        return None

    all_procs = []
    # we iterate over tags, where each tag is dictionary
    for t in tags:
        procs = get_procs(jobs, tag = t, exact_tag_only = exact_tags_only, fmt='orm')
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
                sum_dict = sum_dicts(sum_dict, d)
            # add some useful fields so we can back-reference and
            # also add some sums we obtained in the query
            # we add synthetic alias keys for jobid and cpu_time for
            # a more consistent user experience
            sum_dict.update({'job': j.jobid, 'jobid': j.jobid, 'tags': t, 'num_procs': nprocs, 'num_tids': ntids, 'exclusive_cpu_time': excl_cpu, 'duration': duration, 'cpu_time': excl_cpu})
            all_procs.append(sum_dict)

    if fmt == 'pandas':
        return pd.DataFrame(all_procs)

    # we assume the user wants the output in the form of a list of dicts
    return all_procs

# this function deletes one or more jobs
# It requires 'force' to be set if number of jobs to delete > 1
# Returns: number of jobs deleted or 0 if none deleted.
# The function will either delete all requested jobs or none.
@db_session
def delete_jobs(jobs, force = False):
    #global settings
    #if not(settings.allow_job_deletion):
    #    raise EnvironmentError('allow_job_deletion needs to be True in settings.py to delete jobs')
    jobs = __jobs_col(jobs)
    num_jobs = len(jobs)
    if num_jobs > 1 and not force:
        logger.warning('You must set force=True when calling this function as you want to delete more than one job')
        return 0
    logger.info('deleting %d jobs, in an atomic operation..',len(jobs))
    for j in jobs:
        for p in j.processes:
            p.parent = None
    for j in jobs:
        for p in j.processes:
            p.delete()
    jobs.delete()
    logger.debug('committing deletion')
    commit()
    return num_jobs
