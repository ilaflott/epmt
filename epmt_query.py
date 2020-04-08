from __future__ import print_function
from datetime import datetime, timedelta
import pandas as pd
from orm import *
from json import loads, dumps
from os import environ
from logging import getLogger
import epmt_settings as settings

# do NOT do any epmt imports until logging is set up
# using epmt_logging_init, other than import epmt_logging_init
from epmtlib import epmt_logging_init
logger = getLogger(__name__)  # you can use other name
epmt_logging_init(settings.verbose if hasattr(settings, 'verbose') else 0, check=True)

### Put EPMT imports below, after logging is set up
from epmtlib import tag_from_string, tags_list, init_settings, sum_dicts, unique_dicts, fold_dicts, isString, group_dicts_by_key, stringify_dicts, version, version_str, conv_to_datetime
from epmt_stat import get_classifier_name, is_classifier_mv, mvod_scores, uvod_classifiers

init_settings(settings) # type: ignore
setup_db(settings) # type: ignore

PROC_SUMS_FIELD_IN_JOB='proc_sums'
THREAD_SUMS_FIELD_IN_PROC='threads_sums'


def conv_jobs(jobs, fmt='dict', merge_sums = True):
    """
    conv_jobs will convert 'jobs' from one format to another. 
    The input format need not be specified (it will be auto-detected).
    The output format is specified using 'fmt'.

    jobs: jobs collection (Pony) or a list of Job objects,
          or a list of jobids, or a pandas dataframe or a dictlist of jobs.

    fmt: Output format, one of: 'dict', 'orm', 'pandas' or 'terse'
    
    merge_sums: Is an advanced option. It defaults to True, which means
                underlying sums across processes for a job are shown
                as first-class columns rather than a nested dictionary.
                This option is silently ignored for 'orm' and 'terse' formats.

    """
    _empty_collection_check(jobs)

    jobs = orm_jobs_col(jobs)
    if fmt == 'orm':
        return jobs
    if fmt=='terse':
        return [ j.jobid for j in jobs ]

    # at this point the user wants a dict or dataframe output, so
    # we need to make sure that the jobs have been post-processed
    # I've commented the section below out, and instead we do this
    # in orm_to_dict (that way, whenever the user passes in jobids
    # to convert to dict/pandas, we will make sure proc_sums is 
    # populated). The code below is only for reference as what we
    # could alternatively do:
    # from epmt_job import post_process_job
    # for j in jobs:
    #     if not(is_job_post_processed(j.jobid)):
    #         post_process_job(j)

    # convert the ORM into a list of dictionaries, excluding blacklisted fields
    # and then filter None/empty dicts.
    # It seems in complex error cases we end up with a list containing
    # None items in the list. It's safest to filter them
    # See bug:
    # https://trello.com/c/HfEoCxYU/100-bug-testdaemon-gave-an-exception
    out_list = list(filter(None, [ orm_to_dict(j, exclude = 'processes') for j in jobs ]))

    # do we need to merge process' sum fields into the job?
    if merge_sums:
        for j in out_list:
            # check if dicts have any common fields, if so,
            # warn the user as some fields will get clobbered
            # Note if job hasn't been post-processed it will have an empty (None)
            # PROC_SUMS_FIELD_IN_JOB field. However, orm_to_dict above guarantees
            # all jobs are already post-processed
            common_fields = list(set(j) & set(j[PROC_SUMS_FIELD_IN_JOB]))
            if common_fields:
                logger.warning('while hoisting proc_sums to job-level, found {0} common fields: {1}'.format(len(common_fields), common_fields))
            j.update(j[PROC_SUMS_FIELD_IN_JOB])
            del j[PROC_SUMS_FIELD_IN_JOB]

    return pd.DataFrame(out_list) if fmt=='pandas' else out_list


def __conv_procs_orm(procs, merge_sums = True, fmt='dict'):
    """
    Converts an ORM Query object to a format of choice
    """
    if fmt=='orm':
        return procs

    if fmt=='terse':
        return [ p.id for p in procs ]

    # convert the ORM into a list of dictionaries, excluding blacklisted fields
    out_list = [ orm_to_dict(p, exclude = ['ancestors', 'descendants', 'children', 'threads_df']) for p in procs ]

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


def conv_procs(procs, fmt='pandas', order=None):
    """
    Converts a collection of processes specified in any format
    (orm, pandas, dict-list or terse) to the format specified
    by 'fmt'.
    
    The function makes no claim on the order of the returned
    processes. If you care about the order, you should set the
    'order' argument. It's worth noting that when 'order' is 
    not set, the input order appears to be preserved in all
    cases except sqla+postgres. However, that may change, so
    if you care about the ordering you may need to set 'order'
    """
    _empty_collection_check(procs)

    procs = orm_procs_col(procs)
    if not (order is None):
        procs = procs.order_by(order)
    return __conv_procs_orm(procs, fmt=fmt)


def timeline(jobs, limit=0, fltr='', when=None, hosts=[], fmt='pandas'):
    """
    Timeline returns a timeline of processes ordered chronologically 
    by start time. 

    jobs : Is either a collection of jobs or a single job, where 
           jobs can be specified as jobids or Job objects.
    
    The function takes the same arguments as get_procs is a very
    thin wrapper over it, just setting an ordering by start time.
    
    >>> eq.timeline([u'685000', u'685016'], limit=5)[['job', 'exename', 'start', 'id']]
          job    exename                      start    id
    0  685000       tcsh 2019-06-15 11:52:04.126892  3413
    1  685000       tcsh 2019-06-15 11:52:04.133795  3414
    2  685000      mkdir 2019-06-15 11:52:04.142141  3415
    3  685000  modulecmd 2019-06-15 11:52:04.176020  3416
    4  685000       test 2019-06-15 11:52:04.192758  3417
    
    >>> eq.timeline([u'685000', u'685016'], limit=5, hosts=[Host[u'pp313'], Host[u'pp208']])[['job', 'exename', 'start', 'host']]
          job    exename                      start   host
    0  685000       tcsh 2019-06-15 11:52:04.126892  pp208
    1  685000       tcsh 2019-06-15 11:52:04.133795  pp208
    2  685000      mkdir 2019-06-15 11:52:04.142141  pp208
    3  685000  modulecmd 2019-06-15 11:52:04.176020  pp208
    4  685000       test 2019-06-15 11:52:04.192758  pp208
    """
    return get_procs(jobs, fmt=fmt, order=(Process.start), limit=limit, fltr=fltr, when=when, hosts=hosts)

@db_session 
def get_roots(jobs, fmt='dict'):
    '''
    Returns the root (top-level) processes of a job (or job collection)
    A top-level process is defined as a process with no parent in the
    set of processes that constitute the job.
    '''
    compute_process_trees(jobs)
    return get_procs(jobs, order=Process.start, fltr=((Process.parent == None) if settings.orm == 'sqlalchemy' else 'p.parent == None'), fmt=fmt)

@db_session
def root(job, fmt='dict'):
    """
    Get the root process of a job. The job is either a Job object or a jobid
    If multiple root processes exist, then this returns the first of them
    (by start time)
    
    EXAMPLE:
    >>> eq.root('685016',fmt='terse')
    7266
    
    >>> p = eq.root('685016',fmt='orm')
    >>> p.id
    7266
    >>> p.exename
    u'tcsh'
    >>> p.descendants.count()
    3381
    
    >>> df = eq.root('685016', fmt='pandas')
    >>> df.shape
    (1,49)
    >>> df.loc[0,'pid']
    122181
    
    >>> p = eq.root('685016')
    >>> p['id'],p['exename']
    (7266, u'tcsh')
    """
    # if isString(job):
    #     job = orm_get(Job, job)
    # p = job.processes.order_by(Process.start).limit(1)
    # if fmt == 'orm': return p.to_list().pop()
    # if fmt == 'terse': return p.to_list().pop().id

    # plist = __conv_procs_orm(p, fmt='dict')
    # return pd.DataFrame(plist) if fmt == 'pandas' else plist.pop()
    ret = get_procs(job, order=Process.start, limit=1, fmt=fmt)
    # for all formats other than pandas we just pop the first item
    # from the iterable
    return ret if (fmt == 'pandas') else ret[0]

@db_session
def op_roots(jobs, tag, fmt='dict'):
    """
    This function returns the root process(es) for an operation
    for one or more jobs. Ideally, you would use this function with
    a single job, but we allow a job collection for flexibility.
    Bear in mind, for a large job collection, op_roots is presently a
    *slow* query. 
    
    tag: is a single tag (string or dictionary of key/value pairs)
    
    op_root returns a collection of processes in the format specified.
    The processes are sorted by jobid and within a job by start time
    """
    _empty_collection_check(jobs)
    jobs = orm_jobs_col(jobs)
    compute_process_trees(jobs)
    if not tag:
        logger.error('You must specify a tag (string or dict)')
        return None
    if jobs.count() > 10:
        logger.warning('op_roots is slow currently for job sizes > 10')
    op_procs = get_procs(jobs, tag, fmt='orm')
    if settings.orm == 'sqlalchemy':
        from sqlalchemy.orm import aliased
        ProcessAlias = aliased(Process)
        op_procs_pk = [p.id for p in op_procs]
        root_op_procs = op_procs.join(ProcessAlias, Process.parent).filter(~ProcessAlias.id.in_(op_procs_pk)).order_by(Process.jobid, Process.start)
    else:
        # TODO: This probably can be sped up by partitioning op_procs by job
        root_op_procs = op_procs.filter(lambda p: p.parent not in op_procs).order_by(Process.job, Process.start)
    return __conv_procs_orm(root_op_procs, fmt=fmt)


@db_session
def get_jobs(jobs = [], tags=None, fltr = None, order = None, limit = None, offset = 0, when=None, before=None, after=None, hosts=[], fmt='dict', annotations=None, analyses=None, merge_proc_sums=True, exact_tag_only = False):
    """
    This function returns a list of jobs based on some filtering and ordering.
    The output format can be set to pandas dataframe, list of dicts or list
    of ORM objects based on the 'fmt' option.
    
    jobs   : Optional list of jobs to narrow the search space. The jobs can
             a list of jobids (i.e., list of strings), or the result of a Pony
             query on Job (i.e., a Query object), or a pandas dataframe of jobs
             
    
    tags   : Optional dictionary or string of key/value pairs. If set to ''
             or {}, then exact_tag_match will be implicitly set, and only
             those jobs that have an empty tag will match. 

             For example:
             eq.get_jobs(tags='ocn_res:0.5l75;exp_component:ocean_cobalt_fdet_100')
             gives the job(s) that match *both* ocn_res and exp_component key/values.

             tags may also be specified as a list of strings or dicts. In that 
             case the resulting match is a superset of the matches from the 
             individual tags. For example:
             eq.get_jobs(tags=['ocn_res:0.5l75;exp_component:ocean_cobalt_fdet_100', 'ocn_res:0.5l75;exp_component:ocean_annual_rho2_1x1deg'], fmt='terse')
             This returns a union of jobs that match 'ocn_res:0.5l75;exp_component:ocean_cobalt_fdet_100'
             and those that match 'ocn_res:0.5l75;exp_component:ocean_annual_rho2_1x1deg'

   fltr   : Optional filter whose format will depend on the ORM. 
             For sqlalchemy, you can use something like:
             fltr(Job.jobid == '685000')
             fltr(Job.jobid.in_(['685000', '685016']))

             For Pony, you can use a lamdba function or a string
             e.g., lambda j: count(j.processes) > 100 will filter jobs more than 100 processes
             or, 'j.duration > 100000' will filter jobs whose duration is more than 100000
    
    order  : Optionally sort the output by setting this to a lambda function or string
             e.g, to sort by job duration descending:
                  order = desc(Job.created_at)
             If not set, this defaults to Job.start, in other words
             jobs are returned in the order they were created (not necessarily the
             same as the other of ingestion -- Job.created_at)

             If you are using Pony as the ORM layer, then you can also pass
             in a lambda function, such as:
                 lambda j: j.created_at
             or a string like 'desc(j.created_at)'

    
    limit  : Restrict the output list a specified number of jobs. Defaults to 20.
             When set to 0, it means no limit. There is not default limit when
             using the ORM format. The default applies to all other formats.
    
    offset : When returning query results, skip offset rows. "offset"
             defaults to 0. 
    
    when   : Restrict the output to jobs running at 'when' time. 'when'
             can be specified as a Python datetime. You can also choose
             to specify 'when' as jobid or a Job object. In which 
             case the output will be restricted to those jobs that 
             had an overlap with the specified 'when' job. 'when' may also
             be specified as a string of the form: 'mm/dd/YYYY HH:MM'.

    before : Restrict the output to jobs ended before time specified.
             'before' can be specified either as a python datetime or
             a Unix timestamp or a string. If a negative integer is specified,
             then the time is interpreted as a negative days offset from
             the current time.
                 '08/13/2019 23:29' (string)
                 1565606303 (Unix timestamp)
                 datetime.datetime(2019, 8, 13, 23, 29) (datetime object)
                 -1 => 1 day ago
                 -30 => 30 days ago

    after  : Restrict the output to jobs started after time specified.
             'after' can be specified either as a python datetime or
             a Unix timestamp or a string. If a negative integer is specified,
             then the time is interpreted as a negative days offset from
             the current time.
                 '08/13/2019 23:29' (string)
                 1565606303 (Unix timestamp)
                 datetime.datetime(2019, 8, 13, 23, 29) (datetime object)
                 -1 => 1 day ago
                 -30 => 30 days ago
             
    
    hosts  : Restrict the output to those jobs that ran on 'hosts'.
             'hosts' is a list of hostnames specified as a comma-separated
             string, or a list of strings. A job is considered to match if 
             the intersection of j.hosts and hosts is non-empty
    
    fmt    : Control the output format. One of 'dict', 'pandas', 'orm', 'terse'
             'dict': each job object is converted to a dict, and the entire
                     output is a list of dictionaries
             'pandas': Output a pandas dataframe with one row for each matching job
             'orm':  returns a Pony Query object (ADVANCED)
             'terse': In this format only the primary key ID is printed for each job
    
   annotations: Dictionary of key/value pairs that must ALL match the job 
             annotations. The matching job may have additional key/values.

   analyses: Dictionary of key/value pairs that must ALL match the job
             analyses. The matching job may have additional key/values.

    merge_proc_sums: By default True, which means the fields inside job.proc_sums
             will be hoisted up one level to become first-class members of the job.
             This will make aggregates across processes appear as part of the job
             If False, the job will contain job.proc_sums, which will be a dict
             of key/value pairs, where each is an process attribute, such as numtids,
             and the value is the sum acorss all processes of the job.
    
    exact_tag_only: If set, tag will be considered matched if saved tag
             identically matches the passed tag. The default is False, which
             means if the tag in the database are a superset of the passed
             tag a match will considered.
    """
    from datetime import datetime
    # Customer feedback strongly indicated that limits on the job table were
    # a strong no-no. So, commenting out the code below:
    #
    # set defaults for limit and ordering only if the user doesn't specify jobs
    # if (not(orm_is_query(jobs))) and (type(jobs) != pd.DataFrame) and (jobs in [[], '', None]):
    #     if (fmt != 'orm') and (limit == None): 
    #         limit = 10000
    #         logger.warning('No limit set, defaults to {0}. Set limit=0 to avoid limits'.format(limit))

    if order is None: order = Job.start
      
    qs = orm_jobs_col(jobs)

    if when:
        if type(when) == str:
            try:
                when = datetime.strptime(when, '%m/%d/%Y %H:%M')
            except Exception as e:
                logger.error('could not convert "when" string to datetime: %s' % str(e))
                return None

    if before is not None:
        before = conv_to_datetime(before)

    if after is not None:
        after = conv_to_datetime(after)

    if hosts:
        if isString(hosts):
            # user probably forgot to wrap in a list
            hosts = hosts.split(",")

    qs = orm_get_jobs(qs, tags, fltr, order, limit, offset, when, before, after, hosts, annotations, analyses, exact_tag_only)

    if fmt == 'orm':
        return qs

    return conv_jobs(qs, fmt, merge_proc_sums)


#
@db_session
def get_procs(jobs = [], tags = None, fltr = None, order = None, limit = None, when=None, hosts=[], fmt='dict', merge_threads_sums=True, exact_tag_only = False):
    """
    Filter a supplied list of jobs to find a match
    by tag or some primary keys. If no jobs list is provided,
    then the query will be run against all processes.
    
    All fields are optional and sensible defaults are assumed.
    
    tags: is either a single tag specified as a dictionary or string of 
          key/value pairs, or a list of tags.

          If set to '' or {}, exact_tag_match will be implicitly
          set, and only those processes with an empty tag will match.

          Example of a single tag:

             tags="op_sequence:4;op_instance:3"

             above gives processes that have *both* op_sequence == 4, and op_instance == 3.
             The same can also be specified as:

             tags={'op_sequence': 4, 'op_instance': 3}

          Multiple tags:
             tags may also be specified as a list of strings or dicts. In that 
             case the resulting match is a superset of the matches from the 
             individual tags. For example:
             tags=["op_sequence:4;op_instance:3", "op_sequence:5;op_instance:2"]
             will return the union of procs that match the tag, "op_sequence:4;op_instance:3",
             and the tag - "op_sequence:5;op_instance:2"

    
    fltr:    is a lambda expression or a string of the form:
             lambda p: p.duration > 1000
              OR
             'p.duration > 1000 and p.numtids < 4'

    order:   Order the returned set by the supplied expression.
             For pony, you can use a expression like 'p.created_at'
             or a lambda function.
    
    limit:   If set, limits the total number of results. For formats
             other than 'orm' this defaults to 10000
    
    when   : Restrict the output to processes running at 'when' time. 'when'
             can be specified as a Python datetime. You can also choose
             to specify 'when' as process PK or a Process object. In which 
             case the output will be restricted to those processes that 
             had an overlap with the specified 'when' process. 'when' may also
             be specified as a string of the form: 'mm/dd/YYYY HH:MM'
    
    hosts  : Restrict the output to those processes that ran on 'hosts'.
             'hosts' is a list of hostnames/Host objects. A process is
             consider to match if process.host is in the list of 'hosts'
    
    fmt :   Output format, is one of 'dict', 'orm', 'pandas', 'terse'
            'dict': This is the default, and in this case
                    each process is output as a python dictionary, 
                    and the entire output is a list of dictionaries.
            'pandas': output is a pandas dataframe
            'orm': output is an ORM Query object (ADVANCED)
            'terse': output contains only the database ids of matching processes
    
    merge_threads_sums: By default, this is True, and this means threads sums are
             are folded into the process. If set to False, the threads'
             sums will be available as a separate field THREAD_SUMS_FIELD_IN_PROC.
             Flattening makes subsequent processing easier as all the
             thread aggregates such as 'usertime', 'systemtime' are available
             as first-class members of the process. This option is silently
             ignored if output format 'fmt' is set to 'orm', and ORM
             objects will not be merge_threads_sumsed.
    
    exact_tag_only: If set, tag will be considered matched if saved tag
             identically matches the passed tag. The default is False, which
             means if the tag in the database are a superset of the passed
             tag a match will considered.
    
    For example, to get all processes for a particular Job, with jobid '32046', which
    are multithreaded, you would do:
    
      get_procs(jobs = ['32046'], fltr = 'p.numtids > 1')
    
    To filter all processes that have tags = {'app': 'fft'}, you would do:
    get_procs(tags = {'app': 'fft'})
    
    to get a pandas dataframe:
    qs1 = get_procs(tags = {'app': 'fft'}, fmt = 'pandas')
    
    to filter processes for a job '1234' and order by process duration,
    getting the top 10 results, and keeping the final output in ORM format:
    
    q = get_procs(['1234'], order = 'desc(p.duration)', limit=10, fmt='orm')
    
    now, let's filter processes with duration > 100000 and order them by user+system time,
    and let's get the output into a pandas dataframe:

    q = get_procs(fltr = (lambda p: p.duration > 100000), order = 'desc(p.threads_sums["user+system"]', fmt='pandas')

    Observe, that while 'user+system' is a metric available in the threads_sums field,
    by using the default merge_threads_sums=True, it will be available as column in the output
    dataframe. The output will be pre-sorted on this field because we have set 'order'
    """

    if (limit is None) and (fmt != 'orm'):
        limit = 10000
        logger.warning('No limit set, defaults to {0}. Set limit=0 to avoid limits'.format(limit))

    if when:
        if type(when) == str:
            try:
                when = datetime.strptime(when, '%m/%d/%Y %H:%M')
            except Exception as e:
                logger.error('could not convert "when" string to datetime: %s' % str(e))
                return None

    if hosts:
        if isString(hosts):
            # user probably forgot to wrap in a list
            hosts = hosts.split(",")

    qs = orm_get_procs(jobs, tags, fltr, order, limit, when, hosts, exact_tag_only)

    if fmt == 'orm':
        return qs


    return __conv_procs_orm(qs, merge_threads_sums, fmt)


@db_session
def get_thread_metrics(*processes):
    """
    Returns a thread metrics dataframe for one or more processes
    and None if error,
    where each process is specified as either as a Process object or 
    the database ID of a process.
    If multiple processes are specified then dataframes are concatenated
    using pandas into a single dataframe
    """
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
            p = orm_get(Process, proc)
        else:
            # user supplied process objects directly
            p = proc
        # df = pd.read_json(p.threads_df, orient='split')
        df = pd.DataFrame(p.threads_df)
        # add a synthetic column set to the primary key of the process
        df['process_pk'] = p.id

        df_list.append(df)

    # if we have only one dataframe then no concatenation is needed
    return pd.concat(df_list) if len(df_list) > 1 else df_list[0]


@db_session
def job_proc_tags(jobs, exclude=[], fold=False):
    """
    gets all the unique tags across all processes of a job or collection of jobs

    jobs   : is a single job id or a Job object, or a list of jobids/list of job objects

    fold   : if set to True, this will compact the output to make it more readable
             otherwise, the expanded list of dictionaries is returned

    exclude: an optional list of keys to exclude from each tag (if present)
    """
    _empty_collection_check(jobs)
    jobs = orm_jobs_col(jobs)
    tags = []
    for j in jobs:
        unique_tags_for_job = __unique_proc_tags_for_job(j, exclude, fold = False)
        tags.extend(unique_tags_for_job)
    # remove duplicates
    tags = unique_dicts(tags, exclude)
    return fold_dicts(tags) if fold else tags

# alias job_proc_tags for compat
get_job_proc_tags = job_proc_tags


def rank_proc_tags_keys(jobs, order = 'cardinality', exclude = []):
    '''
    Returns a sorted list of tag keys across processes of one or more jobs.
    The sort order by default is in increasing order of cardinality of the key.
    So a key that has a smaller number of unique values would be earlier in
    the returned list. One can also sort by decreasing frequency, so a key that
    occurred in the most tags would be at before a key that occurred in more
    tags.
      jobs: Collection of one or more jobs or jobids
      order: One of either -- 'cardinality' or 'frequency'. Often they
             will yield the same result as that's the way the tags
             are set in the scripts.
      exclude: List of keys to exclude

    e.g.,
      >>> eq.rank_proc_tags_keys(['685000'])
          [('op', {'ncatted', 'ncrcat', 'dmput', 'fregrid', 'rm', 'timavg', 'hsmget', 'mv', 'cp', 'splitvars', 'untar'}), ('op_instance', {'9', '19', '6', '4', '20', '12', '8', '16', '2', '15', '5', '13', '10', '3', '11', '7', '14', '1', '18'}), ('op_sequence', {'83', '9', '67', '82', '60', '89', '85', '79', '20', '72', '8', '12', '27', '2', '51', '55', '87', '17', '48', '61', '40', '14', '7', '53', '26', '56', '37', '35', '4', '18', '36', '54', '62', '84', '70', '24', '50', '63', '58', '5', '13', '64', '57', '76', '44', '34', '1', '39', '21', '29', '81', '78', '42', '46', '19', '66', '43', '16', '28', '49', '30', '15', '10', '22', '73', '86', '77', '33', '47', '68', '31', '75', '6', '45', '32', '71', '41', '65', '80', '25', '74', '3', '11', '69', '52', '23', '59', '88', '38'})]
      >>> eq.rank_proc_tags_keys(['685000'], order = 'frequency')
      [('op', {'ncatted', 'ncrcat', 'dmput', 'fregrid', 'rm', 'timavg', 'hsmget', 'mv', 'cp', 'splitvars', 'untar'}), ('op_instance', {'9', '19', '6', '4', '20', '12', '8', '16', '2', '15', '5', '13', '10', '3', '11', '7', '14', '1', '18'}), ('op_sequence', {'83', '9', '67', '82', '60', '89', '85', '79', '20', '72', '8', '12', '27', '2', '51', '55', '87', '17', '48', '61', '40', '14', '7', '53', '26', '56', '37', '35', '4', '18', '36', '54', '62', '84', '70', '24', '50', '63', '58', '5', '13', '64', '57', '76', '44', '34', '1', '39', '21', '29', '81', '78', '42', '46', '19', '66', '43', '16', '28', '49', '30', '15', '10', '22', '73', '86', '77', '33', '47', '68', '31', '75', '6', '45', '32', '71', '41', '65', '80', '25', '74', '3', '11', '69', '52', '23', '59', '88', '38'})]
    '''
    _empty_collection_check(jobs)
    if order.lower() not in ('cardinality', 'frequency'):
        logger.warning('order needs to be one or "cardinality" or "frequency"')
        return []
    tags = get_job_proc_tags(jobs, exclude=exclude, fold=False)
    folded_tags = fold_dicts(tags)
    all_keys = list(folded_tags.keys())
    if order.lower() == 'cardinality':
        all_keys.sort(key = lambda k: len(folded_tags[k]))
    elif order.lower() == 'frequency': 
        hist = {}
        for k in all_keys:
            hist[k] = 0
            for t in tags:
                if k in t:
                    hist[k] += 1
        all_keys.sort(key = lambda k: -hist[k])
    return [ (k, set(folded_tags[k])) for k in all_keys ]


@db_session
def get_refmodels(name=None, tag = {}, fltr=None, limit=0, order=None, before=None, after=None, exact_tag_only=False, merge_nested_fields=True, fmt='dict'):
    """
    This function returns reference models filtered using name / tag / fltr
    
    name  : query reference models by name. Usually if you query by name
            you wouldn't need to use tag/fltr/limit/order.
    tag   : refers to a single dict of key/value pairs or a string
    fltr  : a lambda function or a string containing a pony expression
    limit : used to limit the number of output items, 0 means no limit
    order : used to order the output list, its a lambda function or a string
    before : Restrict the output to models created before time specified.
             'before' can be specified either as a python datetime or
             a Unix timestamp or a string. If a negative integer is specified,
             then the time is interpreted as a negative days offset from
             the current time.
                 '08/13/2019 23:29' (string)
                 1565606303 (Unix timestamp)
                 datetime.datetime(2019, 8, 13, 23, 29) (datetime object)
                 -1 => 1 day ago
                 -30 => 30 days ago
    after  : Restrict the output to models created after time specified.
             'after' can be specified either as a python datetime or
             a Unix timestamp or a string. If a negative integer is specified,
             then the time is interpreted as a negative days offset from
             the current time.
                 '08/13/2019 23:29' (string)
                 1565606303 (Unix timestamp)
                 datetime.datetime(2019, 8, 13, 23, 29) (datetime object)
                 -1 => 1 day ago
                 -30 => 30 days ago
    exact_tag_only: is used to match the DB tag with the supplied tag:
            the full dictionary must match for a successful match. Default False.
    merge_nested_fields: used to hoist attributes from the 'computed'
            fields in the reference model, so they appear as first-class fields.
    fmt   : one of 'orm', 'pandas', 'dict' or 'terse'. Default is 'dict'

    EXAMPLE:
      get_refmodels(tag = 'exp_name:ESM4;exp_component:ice_1x1', fmt='pandas')
    """

    # filter using tag if set
    if type(tag) == str:
        tag = tag_from_string(tag)

    if before is not None:
        before = conv_to_datetime(before)
    if after is not None:
        after = conv_to_datetime(after)

    qs = orm_get_refmodels(name, tag, fltr, limit, order, before, after, exact_tag_only)

    if fmt == 'orm':
        return qs

    if fmt == 'terse':
        return [ r.id for r in qs ]
    
    out_list = [ orm_to_dict(r, with_collections=True) for r in qs ]

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
# for univariate classifiers:
#
# { 'z_score': {'duration': (max, median, median_dev), {'cpu_time': (max, median, median_dev)},
#   'iqr': {'duration': ...}
#
# col: is either a dataframe or a collection of jobs (Query/list of Job objects)
def _refmodel_scores(col, methods, features):
    df = conv_jobs(col, fmt='pandas') if col.__class__.__name__ != 'DataFrame' else col
    ret = {}
    logger.info('creating trained model using {0} for features {1}'.format([get_classifier_name(c) for c in methods], features))
    logger.info('jobids: {}'.format(df['jobid'].values))
    for m in methods:
        m_name = get_classifier_name(m)
        ret[m_name] = {}
        if is_classifier_mv(m):
            logger.info('mvod {0}; features ({1})'.format(m_name, features))
            _f = sorted(features)
            nd_array = df[_f].to_numpy()
            # the second element return is a dict indexed by classifier
            # and containing the max anomaly score using the classifier
            retval = mvod_scores(nd_array, classifiers = [m])
            if not retval:
                logger.warning('Skipped mvod classifier {} as could not score using it'.format(m_name))
                del ret[m_name]
                continue
            (full_scores, max_score) = retval
            logger.debug('{0} scores:\n{1}'.format(m_name, full_scores[m_name]))

            # we save the max score and also we need the input nd_array for
            # future reference. We will need the nd_array for outlier detection
            # in detect_outlier_jobs
            ret[m_name][",".join(_f)] = [float(max_score[m_name]), nd_array.tolist()]
        else:
            # univariate classifiers can only handle
            logger.debug('univariate classifier {0}; features {1}'.format(m_name, features))
            for c in features:
                # we save everything returned by the function
                # except the first element, which is a list of scores
                # We really only need the max, median etc
                logger.debug('scoring feature {}'.format(c))
                ret[m_name][c] = m(df[c])[1:]
    # print(ret)
    return ret
#
@db_session
def create_refmodel(jobs=[], name=None, tag={}, op_tags=[], 
                    methods=[], 
                    features=['duration', 'cpu_time', 'num_procs'], exact_tag_only=False,
                    fmt='dict', sanity_check = True, enabled=True, pca=False):
    """
    This function creates a reference model and returns
    the ID of the newly-created model in the database
    
    
    jobs:     points to a list of Jobs (or pony JobSet) or jobids

    name:     An optional string that serves to identify the model
              that will be created. 
    
    tag:      A string or dict consisting of key/value pairs. This
              tag is saved for the refmodel, and may be used
              in a filter while retrieving the model.
    
    op_tags:  A list of strings or dicts. This is optional,
              if set, it will restrict the model to the filtered ops.
              op_tags are distinct from "tag". op_tags are used to
              obtain the set of processes over which an aggregation
              is performed using op_metrics. 
    
    methods: Is a list of methods that are used to obtain outlier
             scores. Each method is passed a vector consisting
             of the value of 'feature' for all the jobs. The
             method will return a vector of scores. This
             vector of scores will be saved (or some processed
             form of it). If methods is not specified then it
             will be determined using the univariate classifers
             defined in settings.
    
    features: List of fields of each job that should be used
             for outlier detection. If passed an empty list
             or a wildcard('*') it will be interpreted as the user
             wanting to use all available metrics for outlier
             detection.
             Defaults to: settings.outlier_features
    
    exact_tag_only: Default False. If set, all tag matches require
             exact dictionary match, and a superset match won't do.

    enabled: Allow the trained model to be used for outlier detection.
             Enabled is set to True by default.

    pca:    False by default. If enabled, the PCA analysis will be done
            on the features prior to creating the model. Rather than setting
            this option to True, you may also set this option to something
            like: pca = 2, in which case it will mean you want two components
            in the PCA. Or something like, pca = 0.95, which will be 
            intepreted as meaning do PCA and automatically select the number
            components to arrive at the number of components in the PCA.
            If set to True, a 0.85 variance ratio will be set to enable
            automatic selection of PCA components.

    
    e.g,.
    
    create a job ref model with a list of jobids
    eq.create_refmodel(jobs=[u'615503', u'625135'], methods= [es.modified_z_score])
    
    or use pony orm query result:
    >>> jobs = eq.get_jobs(tags='exp_component:atmos', fmt='orm')
    >>> r = eq.create_refmodel(jobs)
    
    to create a refmodel for ops we need to either set op_tags
    to a list of tags for the ops, or use the wildcard (*):
    >>> r = eq.create_refmodel(jobs, tag='exp_name:linux_kernel', op_tags='*', methods= [es.modified_z_score])
    
    >>> r['id'], r['tags'], r['jobs']
    (11, {'exp_name': 'linux_kernel'}, [u'kern-6656-20190614-190245', u'kern-6656-20190614-191138', u'kern-6656-20190614-192044-outlier', u'kern-6656-20190614-194024'])
    
    >>> r['op_tags']
    [{u'op_instance': u'4', u'op_sequence': u'4', u'op': u'build'}, {u'op_instance': u'5', u'op_sequence': u'5', u'op': u'clean'}, {u'op_instance': u'3', u'op_sequence': u'3', u'op': u'configure'}, {u'op_instance': u'1', u'op_sequence': u'1', u'op': u'download'}, {u'op_instance': u'2', u'op_sequence': u'2', u'op': u'extract'}]

    Below is an example of creating a refmodel using MV classifiers
    >>> from pyod.models.knn import KNN
    >>> from pyod.models.abod import ABOD
    >>> r = eq.create_refmodel(['625172', '627922', '629337', '633144', '676007', '680181', '685000', '685003', '685016', '692544', '693147', '696127'], methods = [ABOD(), KNN()], features = ['cpu_time', 'duration', 'num_procs'])
    WARNING: epmt_query: The jobs do not share identical tag values for "exp_name" and "exp_component"
    WARNING: The jobs do not share identical tag values for "exp_name" and "exp_component"
        685000 ESM4_historical_D151 ocean_annual_rho2_1x1deg
        685003 ESM4_historical_D151 ocean_cobalt_fdet_100
        685016 ESM4_historical_D151 ocean_month_rho2_1x1deg
        625172 ESM4_historical_D151 ocean_month_rho2_1x1deg
        693147 ESM4_historical_D151 ocean_month_rho2_1x1deg
        692544 ESM4_historical_D151 ocean_month_rho2_1x1deg
        696127 ESM4_historical_D151 ocean_month_rho2_1x1deg
        627922 ESM4_historical_D151 ocean_month_rho2_1x1deg
        629337 ESM4_historical_D151 ocean_month_rho2_1x1deg
        633144 ESM4_historical_D151 ocean_month_rho2_1x1deg
        676007 ESM4_historical_D151 ocean_month_rho2_1x1deg
        680181 ESM4_historical_D151 ocean_month_rho2_1x1deg
    >>> r
    {'jobs': ['685000', '685003', '685016', '625172', '693147', '692544', '696127', '627922', '629337', '633144', '676007', '680181'], 'name': None, 'tags': {}, 'op_tags': [], 'computed': {'pyod.models.abod': {'cpu_time,duration,num_procs': -3.478362573453902e-40}, 'pyod.models.knn': {'cpu_time,duration,num_procs': 6014539197.113887}}, 'enabled': True, 'id': 6, 'created_at': datetime.datetime(2020, 2, 3, 17, 6, 59, 501012)}

    """
    if not jobs or (not(orm_is_query(jobs)) and len(jobs)==0) or (orm_is_query(jobs) and (jobs.count == 0)):
        logger.error('You need to specify one or more jobs to create a reference model')
        return None

    if type(tag) == str:
        tag = tag_from_string(tag)

    methods = methods or uvod_classifiers()

    # do we have a list of jobids?
    # if so, we need to get the actual DB objects for them
    #if type(jobs) == set:
    #    jobs = list(jobs)
    #if type(jobs) == list and isString(jobs[0]):
    #    jobs = Job.select(lambda j: j.jobid in jobs)
    
    jobs_orm = orm_jobs_col(jobs)
    jobs_df = conv_jobs(jobs_orm, fmt='pandas')
    jobs = jobs_orm[:]
    from epmt_outliers import sanitize_features
    if (len(jobs) < 3):
        logger.error('You cannot create a model with less than 3 jobs. Your chosen jobs: {}'.format(jobs))
        return False

    if sanity_check:
        _warn_incomparable_jobs(jobs)

    if pca and features and (features != '*'):
        logger.warning('It is strongly recommended to set features=[] when doing PCA')
    features = sanitize_features(features, jobs_df)
    orig_features = features  # keep a copy as features might be reassigned below
    if pca:
        logger.info("request to do PCA (pca={}). Input features: {}".format(pca, features))
        if len(features) < 5:
            logger.warning('Too few input features for PCA. Are you sure you did not want to set features=[] to enable selecting all available features?')
        from epmt_outliers import pca_feature_combine
        import numpy as np

    if op_tags:
        if op_tags == '*':
            logger.info('wildcard op_tags set: obtaining set of unique tags across the input jobs')
            op_tags = job_proc_tags(jobs_orm, fold=False)
        # do we have a single tag in string or dict form? 
        # we eventually want a list of dicts
        # elif type(op_tags) == str:
        #     op_tags = [tag_from_string(op_tags)]
        # elif type(op_tags) == dict:
        #     op_tags = [op_tags]
        else:
            op_tags = tags_list(op_tags)
        # let's get the dataframe of metrics aggregated by op_tags
        ops_df = get_op_metrics(jobs = jobs_orm, tags = op_tags, exact_tags_only = exact_tag_only, fmt='pandas')
        logger.debug('jobid,tags:\n{}'.format(ops_df[['jobid','tags']]))
        if pca:
            (ops_pca_df, pca_variances, pca_features, _) = pca_feature_combine(ops_df, features, desired = 0.85 if pca is True else pca)
            logger.info('{} PCA components obtained: {}'.format(len(pca_features), pca_features))
            logger.info('PCA variances: {} (sum={})'.format(pca_variances, np.sum(pca_variances)))
            ops_df = ops_pca_df
            features = pca_features

        scores = {}
        for t in op_tags:
            # serialize the tag so we can use it as a key
            stag = dumps(t, sort_keys=True)
            # pylint: disable=no-member
            logger.debug('scoring op {}'.format(t))
            scores[stag] = _refmodel_scores(ops_df[ops_df.tags == t], methods, features)
    else:
        # full jobs, no ops
        logger.debug('jobid,tags:\n{}'.format(jobs_df[['jobid','tags']]))
        if pca:
            (jobs_pca_df, pca_variances, pca_features, _) = pca_feature_combine(jobs_df, features, desired = 0.85 if pca is True else pca)
            logger.info('{} PCA components obtained: {}'.format(len(pca_features), pca_features))
            logger.info('PCA variances: {} (sum={})'.format(pca_variances, np.sum(pca_variances)))
            jobs_df = jobs_pca_df
            features = pca_features
        scores = _refmodel_scores(jobs_df, methods, features)

    logger.debug('computed scores: {0}'.format(scores))
    computed = scores

    # if we use pca, then we need to save the input feature names
    # for future reference. To be safe, we also save the output PCA
    # feature names
    info_dict = {}
    if pca:
        info_dict['pca'] = { 'inp_features': orig_features, 'out_features': pca_features }

    # now save the ref model
    r = ReferenceModel(jobs=jobs, name=name, tags=tag, op_tags=op_tags, computed=computed, info_dict = info_dict, enabled=enabled)
    orm_commit()
    if fmt=='orm': 
        return r
    elif fmt=='terse': 
        return r.id
    r_dict = orm_to_dict(r, with_collections=True)
    return pd.Series(r_dict) if fmt=='pandas' else r_dict

# returns the number of models deleted.
@db_session
def delete_refmodels(*ref_ids):
    """
    Deletes one or more reference models. The reference models are specified
    using their IDs. The functions the returns the number of reference models
    deleted (either all the requested models will be deleted or none (0))
    """
    if not ref_ids:
        logger.warning("You must specify one or more reference model IDs to delete")
        return 0
    if type(ref_ids[0]) == list:
        # user already gave a list of ids
        ref_ids = ref_ids[0]
    ref_ids = [int(r) for r in ref_ids]
    return orm_delete_refmodels(ref_ids)

def retire_refmodels(ndays = settings.retire_models_ndays):
    """
    Retire models older than ndays (ndays > 0). If ndays is
    specified as <= 0 then it's a nop. On success it returns
    the number of models deleted.
    """
    if ndays <= 0: return 0

    # ndays > 0
    models = get_refmodels(before=-ndays, fmt='terse')
    if models:
        logger.info('Retiring following models (older than %d days): %s', ndays, str(models))
        return delete_refmodels(models)
    else:
        logger.info('No models to retire (older than %d days)', ndays)
    return 0

def refmodel_set_enabled(ref_id, enabled = False):
    """
    Enable or disable a trained model.
    """
    r = ReferenceModel[ref_id]
    r.enabled = enabled
    return r

def refmodel_is_enabled(ref_id):
    """
    Get the status (enabled/disabled) of a trained model.
    """
    return ReferenceModel[ref_id].enabled

def refmodel_get_metrics(model, active_only = False):
    """
    Get the set of metrics available in a trained model.
    If 'active_only' is set then only the active metrics are returned.
    """
    r = ReferenceModel[model] if (type(model) == int) else model
    metrics = set()
    # iterate over the dicts stored for each method and do a union operation
    # print(r.computed)
    for v in r.computed.values():
        # op models have the metrics further nested so here we do a try/catch
        # first with the deeper nest and then one less. 
        try:
            m = []
            for _v in v.values():
                # print(_v)
                m += _v.keys()
        except:
            m = v.keys()
        metrics |= set(m)

    # see if we have any PCA features
    pca_features = (r.info_dict or {}).get('pca', {}).get('inp_features', [])
    if pca_features:
        logger.debug('PCA features found in model: {}'.format(pca_features))
        metrics |= set(pca_features)

    if active_only:
        active_metrics = (r.info_dict or {}).get('active_metrics', [])
        if active_metrics:
            # do an intersection
            metrics &= set(active_metrics)

    # while metrics should consist of features that are each singular
    # it might also consist of a MV feature set like "duration,num_procs,cpu_time"
    # In other words a composite feature set. We need to break them down
    decomposed_metrics = set()
    for f in metrics:
        if "," in f:
            decomp_features = f.split(",")
            decomposed_metrics |= set(decomp_features)
        else:
            decomposed_metrics.add(f)
    return decomposed_metrics

def refmodel_set_active_metrics(ref_id, metrics):
    """
    Set the active metrics for a trained model to specified list of metrics.
    """
    r = ReferenceModel[ref_id]
    all_metrics = refmodel_get_metrics(ref_id, False)
    metrics_set = set(metrics)
    if (metrics_set - all_metrics):
        logger.warning('Ignoring metrics that are not available in the trained model: {0}'.format(metrics_set - all_metrics))
    active_metrics = list(metrics_set & all_metrics)
    logger.info('Active metrics for model set to: %s',str(active_metrics))
    info_dict = dict.copy(r.info_dict or {})
    info_dict['active_metrics'] = active_metrics
    r.info_dict = info_dict
    return active_metrics


            
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
        tags = proc_sums['all_proc_tags']
    except:
        # if we haven't found it the easy way, do the heavy compute
        import numpy as np
        tags = np.unique(np.array(job.processes.tags)).tolist()

    # get unique dicts after removing exclude keys
    if exclude:
        tags = unique_dicts(tags, exclude)

    return fold_dicts(tags) if fold else tags


@db_session
def get_ops(jobs, tags = [], exact_tag_only = False, combine=False, fmt='dict', op_duration_method = "sum", full= False):
    '''
    Returns a collection of "Operations", where each Operation is either
    an object, a dict, or a dataframe row, depending on 'fmt'. An operation represents a collection
    of processes that share a tag. 

    jobs: Collection of jobs. For e.g., a list of jobids, etc.

    tags: List of tags, where each tag is a dictionary of key/value pairs.
          As in `get_procs`, a tag may also be specified as a string. Hence,
          tags can be a list of strings.
          You may also specify a single key, such as 'op' for tags. In this
          case the expansion assumes a wildcard for the key to cover all
          possible values for that key over the jobs set. If not specified,
          the jobs will be queried for the tag key with the lowest cardinality
          and that key will be used.

    exact_tag_only: Advanced option, that requires each tag to be exactly
          matched. By default (exact_tag_only = False), a process tag is
          considered to be a match for a tag, t, if the process tag is a superset
          of t.

    fmt: Output format for each operation in the returned collection.
         If set to 'dict' a list of dictionaries is returned. If 'orm'
         then a list of ORM Operation objects are returned. If 'pandas'
         a dataframe is returned, where each row represents an operation.
         'terse' format is not supported, and will be silently translated
         to 'dict'.

    combine: If combine is set to True, then the returned list of operations
          will be combined into a single high-level operation. In this case
          the returned value will a list with a single operation.
          The main use of this is to merge the execution intervals and proc_sums.

    op_duration_method: One of "sum", "sum-minus-overlap" or "finish-minus-start"
                  sum: signifies a dumb sum of process durations
                  sum-minus-overlap: expensive computation that ensures overlapping
                       processes are not double-counted.
                  finish-minus-start: operation duration is calculated as the
                       difference of the last process to finish and the first
                       process to start. 
                  Defaults to "sum"

    full: This argument is False by default. Its only useful when format is set to
          dict. With this option enabled, the full Operation object including
          expensive fields to compute such as intervals, are computed and 
          included in the dictionary. This is an expensive option, so it's disabled
          by default. (ADVANCED)

    EXAMPLES:
          To get the ops as a list of dicts for two distinct tags, do:

          >>> ops = get_ops(['685000', '685003'], tags = ['op:timavg', 'op:ncks'])
          >>> len(ops)
          2
          >>> ops[0]['duration'], ops[1]['duration']
          (36053215.00000002, 4773814.999999999)


          Below we do the same but this time we get a list of ORM objects:

          >>> ops_orm = get_ops(['685000', '685003'], tags = [{ 'op':'timavg'}, {'op':'ncks'}], fmt='orm')
          >>> [o.duration for o in ops_orm]
          [36053215.00000002, 4773814.999999999]
           
          Now suppose we want to combine the returned operations into a single operation:

          >>> ops = get_ops(['685000', '685003'],tags =['op:timavg', 'op:ncks'],combine=True, fmt='orm')
          >>> hl_op = ops[0]   # ops only has one element when combine is True
          >>> hl_op.start, hl_op.end, hl_op.duration, hl_op.num_runs()
          (datetime.datetime(2019, 6, 15, 13, 38, 25, 618279), datetime.datetime(2019, 6, 15, 13, 42, 18, 345456), 40827030.00000001, 159)


          Rather than specifying the tags, we can just mention the key
          we care about. This will be auto-expanded:

          >>> op = get_ops(['685000', '685003'], tags = 'op', combine=True)[0]
          DEBUG:epmt_query:expanding op for values ['splitvars', 'untar', 'dmput', 'ncatted', 'ncks', 'cp', 'timavg', 'hsmget', 'ncrcat', 'rm', 'fregrid', 'mv']
          DEBUG:epmt_query:tags: [{'op': 'splitvars'}, {'op': 'untar'}, {'op': 'dmput'}, {'op': 'ncatted'}, {'op': 'ncks'}, {'op': 'cp'}, {'op': 'timavg'}, {'op': 'hsmget'}, {'op': 'ncrcat'}, {'op': 'rm'}, {'op': 'fregrid'}, {'op': 'mv'}]


          If we are lazy and only want the top-level ops (based on the tag of most importance):

          >>> ops = eq.get_ops(['685000', '685003'], tags = '')
          DEBUG:epmt_query:no tag specified, using tags: op
          DEBUG:epmt_query:expanding op for values ['splitvars', 'untar', 'dmput', 'ncatted', 'ncks', 'cp', 'timavg', 'hsmget', 'ncrcat', 'rm', 'fregrid', 'mv']
          DEBUG:epmt_query:tags: [{'op': 'splitvars'}, {'op': 'untar'}, {'op': 'dmput'}, {'op': 'ncatted'}, {'op': 'ncks'}, {'op': 'cp'}, {'op': 'timavg'}, {'op': 'hsmget'}, {'op': 'ncrcat'}, {'op': 'rm'}, {'op': 'fregrid'}, {'op': 'mv'}]
          >>> len(ops)
          12
    '''
    _empty_collection_check(jobs)
    if not tags:
        tags = rank_proc_tags_keys(jobs)[0][0]
        logger.debug('no tag specified, using tags: {0}'.format(tags))

    if type(tags) != list:
        tags = [tags]

    # expand compressed tags, if any
    _tags = []
    job_proc_tags = get_job_proc_tags(jobs, fold=True)
    for t in tags:
        if isString(t) and not(':' in t):
            # this means we have specified a label such as 'op'
            # and we want to expand that into a list of tags such as
            # [{'op': 'timavg'}, {'op': 'dmget'},...]
            tag_values = job_proc_tags.get(t, [])
            logger.debug('expanding {0} for values {1}'.format(t, tag_values))
            for v in tag_values:
                _tags.append({ t: v })
        else:
            _tags.append(t)
    logger.debug('tags: {0}'.format(_tags))

    if combine:
        # Operation will pass the list of tags to get_procs
        # and the entire set of processes will be considered
        # as one operation
        ops = [Operation(jobs, _tags, exact_tag_only, op_duration_method = op_duration_method)]
    else:
        ops = []
        for t in _tags:
            op = Operation(jobs, t, exact_tag_only, op_duration_method = op_duration_method)
            if op: ops.append(op)

    if fmt != 'orm':
        ops = [ op.to_dict(full=full) for op in ops ]
        if fmt == 'pandas':
            ops = pd.DataFrame(ops)
    return ops

@db_session
def get_op_metrics(jobs = [], tags = [], exact_tags_only = False, group_by_tag=False, fmt='pandas', op_duration_method = "sum"):
    """
    Aggregates metrics across processes for one or or more operations.
    The returned output is of the form:

    <job-id>,<tag1>, metric11, metric12, ...
    <job-id>,<tag2>, metric21, metric22, ...

    where, <metric11> is the sum across process for the tag1 for metric1

    jobs        : Is a single job or a collection of jobs

    tags        : List of strings or a list of dictionaries. You may also
                  pass a single tag as a string or dict. If no tags are supplied, 
                  then the set of unique tags for the jobs will be used.
    
    exact_tags  : If exact_tags_only is set (default False), then a match
                  means there is an exact match of the tag dictionaries.

    group_by_tag: If set, rows that have the same tag will be coalesced
                  and their column values will be aggregated. As a 
                  consequence, the output will not have job/jobid columns
    
    fmt:          One of 'dict' or 'pandas'. Defaults to 'pandas'

    op_duration_method: One of "sum", "sum-minus-overlap" or "finish-minus-start"
                  sum: signifies a dumb sum of process durations
                  sum-minus-overlap: expensive computation that ensures overlapping
                       processes are not double-counted.
                  finish-minus-start: operation duration is calculated as the
                       difference of the last process to finish and the first
                       process to start. 
                  Defaults to "sum"
    """
    if op_duration_method not in ("sum", "sum-minus-overlap", "finish-minus-start"):
        raise ValueError('op_duration_method must be one of ("sum", "sum-minus-overlap", "finish-minus-start")')
    _empty_collection_check(jobs)
    jobs = orm_jobs_col(jobs).order_by(Job.start)

    if jobs.count() == 0:
        logger.warning('You need to specify one or more jobs for op_metrics')
        return None

    if isString(jobs):
        jobs = [jobs]

    tags = tags_list(tags) if tags else job_proc_tags(jobs, fold=False)
    if not tags:
        logger.warning('No tags found across all processes of job(s)')
        return None
    #from hashlib import md5
    #print(md5(str(stringify_dicts(tags)).encode('utf-8')).hexdigest())

    all_procs = []
    # we iterate over tags, where each tag is dictionary
    for t in tags:

        # group the Query response we got by jobid
        # we use group_concat to join the thread_sums json into a giant string
        if settings.orm == 'sqlalchemy':
            if 'postgres' in settings.db_params.get('url', ''):
                # postgres doesn't have an group_concat, so we first aggregate into an
                # an array and then join the array elements into a string using a separator
                concat_threads_sums = func.array_to_string(func.array_agg(Process.threads_sums), '@@@')
            else:
                concat_threads_sums = func.group_concat(Process.threads_sums, '@@@')
            procs_grp_by_job = orm_get_procs(jobs, t, None, None, 0, None, [], exact_tags_only, [Process.jobid, func.count(Process.id), func.min(Process.start), func.max(Process.end), func.sum(Process.duration), func.sum(Process.cpu_time), func.sum(Process.numtids), concat_threads_sums]).group_by(Process.jobid).order_by(Process.jobid)
        else:
            # Pony ORM
            procs = get_procs(jobs, tags = t, exact_tag_only = exact_tags_only, fmt='orm')
            procs_grp_by_job = select((p.job, count(p.id), min(p.start), max(p.end), sum(p.duration), sum(p.cpu_time), sum(p.numtids), group_concat(p.threads_sums, sep='@@@')) for p in procs)

        for row in procs_grp_by_job:
            (j, nprocs, start, end, duration, excl_cpu, ntids, threads_sums_str) = row
            if op_duration_method == "finish-minus-start":
                duration = (end - start).total_seconds() * 1e6
            elif op_duration_method == "sum-minus-overlap":
                # duration calculation requires us to account for
                # overlapping processes in an operation (since one may
                # background and wait). 
                # So we use Operation to correctly compute duration
                # This is an expensive computation:
                # O(NlogN) complexity, where N is the num. of processes
                op = Operation(j, t, exact_tags_only, op_duration_method = "sum-minus-overlap")
                duration = round(op.duration,1)
            elif op_duration_method == "sum":
                # nop since we already computed that in 'duration' using the ORM
                pass
            else:
                raise ValueError("Do not know how to handle op_duration_method: {}".format(op_duration_method))
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
            jobid = j.jobid if (type(j) == Job) else j
            sum_dict.update({'job': jobid, 'jobid': jobid, 'tags': t, 'num_procs': nprocs, 'numtids': ntids, 'cpu_time': excl_cpu, 'duration': duration})
            all_procs.append(sum_dict)

    if group_by_tag:
        all_procs = group_dicts_by_key(all_procs, key='tags', exclude=['job', 'jobid'])

    if fmt == 'pandas':
        return pd.DataFrame(all_procs)

    # we assume the user wants the output in the form of a list of dicts
    return all_procs

# alias for get_op_metrics, for compat
op_metrics = get_op_metrics

@db_session
def delete_jobs(jobs, force = False, before=None, after=None, warn = True):
    """
    Deletes one or more jobs and returns the number of jobs deleted.

    jobs  : One or more jobs. [] selects all jobs. You would normally
            use [] with 'before' or 'after' options.

    force : By default, False. 'force' has to be set to True to allow
            deletion of multiple jobs.

    before,
    after : time specified as cutoff. See 'get_jobs' to see how to specify
            these options.

     warn : This option is only used in daemon mode where we want to 
            disable unnecessary copious warnings in logs.
            Default True. When disabled, no warnings will be given about attempting
            to delete jobs that have models associated with them. Instead
            those jobs will be skipped.
            

    The function will either delete all requested jobs or none. The delete
    is done in an atomic transaction.

    EXAMPLE:
        # to delete multiple jobs
        delete_jobs(['685003', '685016'], force=True)

        # to delete ALL jobs. Careful!!
        delete_jobs([], force=True)

        # deletes all jobs older than 30 days
        delete_jobs([], force=True, before=-30)

        # delete jobs before Jan 21, 2018 09:55
        delete_jobs([], force=True, before='01/21/2018 09:55')

        # delete jobs executed in the last 7 days
        delete_jobs([], force=True, after=-7)

    """

    jobs = orm_jobs_col(jobs)

    if ((before != None) or (after != None)):
        jobs = get_jobs(jobs, before=before, after=after, fmt='orm')

    num_jobs = jobs.count()
    if num_jobs == 0:
        if warn:
            logger.warning('No jobs matched; none deleted')
        return 0
    if num_jobs > 1 and not force:
        logger.warning('set force=True when calling this function if deleting more than one job')
        return 0

    # make sure we aren't trying to delete jobs with models associated with them
    jobs_with_models = {}
    jobs_to_delete = []
    for j in jobs:
        if j.ref_models: 
            jobs_with_models[j.jobid] = [r.id for r in j.ref_models]
        else:
            jobs_to_delete.append(j.jobid)
    if jobs_with_models:
        if warn:
            logger.warning('The following jobs have models (their IDs have been mentioned in square brackets) associated with them and these jobs will not be deleted:\n\t%s\n', str(jobs_with_models))
        if not jobs_to_delete:
            logger.info('No jobs match criteria to delete. Bailing..')
            return 0
        jobs = orm_jobs_col(jobs_to_delete)
        num_jobs = len(jobs_to_delete)
    logger.info('deleting %d jobs (%s), in an atomic operation..', num_jobs, str(jobs_to_delete))
    orm_delete_jobs(jobs)
    return num_jobs


def retire_jobs(ndays = settings.retire_jobs_ndays):
    """
    Retires jobs older than 'ndays' and returns the list of jobs retired.

    ndays must be > 0 for any jobs to be retired. For ndays <=0, no jobs
    are retired.
    """
    if ndays <= 0: return 0
    return delete_jobs([], force=True, before = -ndays, warn = False)

@db_session
def dm_calc(jobs = [], tags = ['op:hsmput', 'op:dmget', 'op:untar', 'op:mv', 'op:dmput', 'op:hsmget', 'op:rm', 'op:cp']):
    """
    This function has a high memory footprint, and you should only use it
    for small collection of jobs (len(jobs) < 100). For large collections
    use dm_calc_iter instead
    """
    _empty_collection_check(jobs)
    logger.debug('dm ops: {0}'.format(tags))
    jobs = orm_jobs_col(jobs)
    num_jobs = jobs.count()
    logger.debug('number of jobs: {0}'.format(num_jobs))
    if (num_jobs > 100):
        logger.warning('job count ({0}) > 100: it is recommended to use dm_calc_iter instead for a lower memory footprint and faster time-to-solution'.format(num_jobs))
    tags = tags_list(tags)
    dm_ops_df = op_metrics(jobs, tags = tags, group_by_tag = True)
    jobs_cpu_time = 0.0
    for j in jobs:
        jobs_cpu_time += j.cpu_time
    dm_cpu_time = dm_ops_df['cpu_time'].sum()
    dm_percent = round((100 * dm_cpu_time / jobs_cpu_time), 2)
    return (dm_percent, dm_ops_df, jobs_cpu_time)

@db_session
def dm_calc_iter(jobs = [], tags = ['op:hsmput', 'op:dmget', 'op:untar', 'op:mv', 'op:dmput', 'op:hsmget', 'op:rm', 'op:cp'], features = ['cpu_time']):
    """
    This does the same data movement calculation as dm_calc, but has
    a *far lower memory footprint, and is twice as fast*. Plus it
    produces an additional dataframe that aggregates across tags by job
    allowing us to compute min/max/std_dev across jobs for DM.
    """
    from datetime import datetime
    logger.debug('dm ops: {0}'.format(tags))
    jobs = orm_jobs_col(jobs)
    logger.debug('number of jobs: {0}'.format(jobs.count))
    tags = tags_list(tags)
    jobs_cpu_time = 0.0
    df_list = []
    agg_ops_by_job = []
    n = 0
    start_time = datetime.now()
    for j in jobs:
        n += 1
        jobs_cpu_time += j.cpu_time
        job_dm_ops_df = op_metrics(j, tags = tags, group_by_tag = True)
        job_dm_ops_df.insert(0, 'jobid', j.jobid)
        df_list.append(job_dm_ops_df)
        agg_dict = {'jobid': j.jobid, 'job_cpu_time': j.cpu_time}
        for f in features:
            agg_dict['dm_' + f] = job_dm_ops_df[f].sum()
            if hasattr(j, f):
                job_total = getattr(j, f)
                if job_total != 0:
                    agg_dict['dm_' + f + '%'] = round(100*agg_dict['dm_' + f]/job_total)
        agg_ops_by_job.append(agg_dict)
        if (n % 10 == 0):
            elapsed_time = datetime.now() - start_time
            logger.debug('processed %d of %d jobs at %.2f jobs/sec', n, len(jobs), n/elapsed_time.total_seconds())
    dm_ops_df = pd.concat(df_list).reset_index(drop=True)
    dm_agg_df_by_job = pd.DataFrame(agg_ops_by_job)
    dm_cpu_time = dm_ops_df['cpu_time'].sum()
    dm_percent = round((100 * dm_cpu_time / jobs_cpu_time), 3)
    return (dm_percent, dm_ops_df, jobs_cpu_time, dm_agg_df_by_job)

@db_session
def get_job_status(jobid):
    '''
    Returns the job status dictionary, which consists of the following job fields:
      - script_path
      - script
      - stdout
      - stderr
      - exit_reason
      - exit_status

    If the job status has not been populated, the function will return an
    empty dictionary.
    '''
    j = orm_get(Job, jobid) if (type(jobid) == str) else jobid
    return j.info_dict.get('status', {})

@db_session
def annotate_job(jobid, annotation, replace=False):
    '''
    Annotates a job
      - annotation is a dictionary of key/value pairs
        If replace is True, then *all* existing annotations
        will be overritten. Normally, this is set to False,
        in which case, the supplied annotations are merged into
        the existing annotations.

    Returns the new annotations for the job.
    '''
    j = Job[jobid] if (type(jobid) == str) else jobid
    if type(annotation) == str:
        annotation = tag_from_string(annotation)
    ann = {} if replace else dict(j.annotations)
    ann.update(annotation)
    j.annotations = ann
    orm_commit()
    return ann

@db_session
def get_job_annotations(jobid):
    '''
    Returns the annotations (if any) for a job
    '''
    j = orm_get(Job, jobid) if (type(jobid) == str) else jobid
    return j.annotations

def remove_job_annotations(jobid):
    return annotate_job(jobid, {}, True)

def analyze_pending_jobs(jobs = [], analyses_filter = {}):
    """
    Analyze all pending jobs. The jobs may or may not be
    comparable. 
    
    jobs: Restrict applying the analyses to a subset specified by jobs.
          In the most common usage, you will leave jobs unset.

    analyses_filter: This tag defines what constitutes an unanalyzed job

    Returns: The total number of analyses algorithms executed
    """
    ua_jobs = get_unanalyzed_jobs(jobs = jobs, analyses_filter = analyses_filter)
    num_analyses_run = 0
    if ua_jobs:
        logger.debug('{0} unanalyzed jobs: {1}'.format(len(ua_jobs), ua_jobs))
        # partition the jobs into sets of comparable jobs based on their tags
        comp_job_parts = comparable_job_partitions(ua_jobs)
        logger.debug('{0} sets of comparable jobs: {1}'.format(len(comp_job_parts), comp_job_parts))
        # iterate over the comparable jobs' sets
        for j_part in comp_job_parts:
            (_, jobids) = j_part
            # we set check_comparable as False since we already know
            # that the jobs are comparable -- don't waste time!
            num_analyses_run += analyze_comparable_jobs(jobids, check_comparable = False)
    return num_analyses_run



@db_session
def analyze_comparable_jobs(jobids, check_comparable = True, keys = ('exp_name', 'exp_component')):
    """
    Analyzes one or more jobs. The jobs must be comparable; a warning
    will be issued if they aren't (unless check_comparable is disabled).
    You may want to use the higher-level function -- analyze_pending_jobs -- instead.

    jobids: List of job ids

    keys: is a tuple of job tag keys that will be used to query for
    trained models. If trained model(s) are found then outlier detection
    is run on the jobs against the trained model(s).

    It's possible no trained model is found, then we will do an outlier
    detection on the job set (partition_jobs) assuming that's possible.

    Returns: Number of analyses algorithms executed. This may be zero
             if number of comparable jobs are too few and there are
             no trained models.
    """
    from epmt_outliers import detect_outlier_jobs
    if check_comparable:
        _warn_incomparable_jobs(jobids)
    logger.debug('analyzing jobs: {0}'.format(jobids))
    model_tag = {}
    for k in keys:
        model_tag[k] = Job[jobids[0]].tags.get(k, '')
        # make sure all the jobids have the same value for the tag key
        if check_comparable:
            for j in jobids:
                v = jobids[j].tags.get(k, '')
                if not k in jobids[j].tags:
                    logger.warning('job {0} tags has no key -- {1}'.format(j, k))
                assert(jobids[j].tags.get(k, '') == model_tag[k])
    logger.debug('Searching for trained models with tag: {0}'.format(model_tag))
    trained_models = get_refmodels(tag = model_tag)
    outlier_results = []
    # can we make the if/then more DNRY?
    if trained_models:
        logger.debug('found {0} trained models for job set'.format(len(trained_models)))
        for r in trained_models:
            model_id = r['id']
            d = detect_outlier_jobs(jobids, trained_model = model_id)[1]
            # make the results JSON serializable (sets aren't unfortunately)
            outlier_detect_results = { k: (list(v[0]), list(v[1])) for k, v in d.items() }
            outlier_results.append({'model_id': model_id, 'results': outlier_detect_results})
    else:
        # no trained model found. 
        # Can we run a detect_outlier_jobs on the exisiting job set?
        if len(jobids) < 4:
            logger.warning('{0} -- No trained model found, and too few jobs for outlier detection (need at least 4)'.format(jobids))
        else:
            d = detect_outlier_jobs(jobids)[1]
            # make the results JSON serializable (sets aren't unfortunately)
            outlier_detect_results = { k: (list(v[0]), list(v[1])) for k, v in d.items() }
            outlier_results.append({'model_id': None, 'results': outlier_detect_results})
    analyses = { 'outlier_detection': outlier_results }
    num_analyses_runs = len(outlier_results)

    # finally mark the jobs as analyzed
    for j in jobids:
        set_job_analyses(j, analyses)
    msg = 'analyzed {0}: '.format(jobids)
    for k in analyses:
        msg += '{0} runs of {1}; '.format(len(analyses[k]), k)
    logger.info(msg)
    return num_analyses_runs

@db_session
def set_job_analyses(jobid, analyses, replace=False):
    '''
    Saves analyses data/metadata for a job
      - analyses is a dictionary of key/value pairs
        If replace is True, then *all* existing analyses
        will be overritten. Normally, this is set to False,
        in which case, the supplied analyses are merged into
        the existing analyses.

    Returns the updated analyses for the job.
    '''
    j = orm_get(Job, jobid) if (type(jobid) == str) else jobid
    full_analyses = {} if replace else dict(j.analyses)
    full_analyses.update(analyses)
    j.analyses = full_analyses
    orm_commit()
    return full_analyses

@db_session
def get_job_analyses(jobid):
    '''  
    Returns the analyses for a job
    '''
    j = orm_get(Job, jobid) if (type(jobid) == str) else jobid
    return j.analyses

def get_unanalyzed_jobs(jobs = [], analyses_filter = {}, fmt='terse'):
    '''
    Returns the subset of jobs that have not had any analysis pipeline
    run on them.
    '''
    return get_jobs(jobs, analyses = analyses_filter, fmt=fmt)


def remove_job_analyses(jobid):
    return set_job_analyses(jobid, {}, True)

@db_session
def get_unprocessed_jobs():
    '''
    Returns the list of jobids that have not been subjected to
    post-processing during ingestion
    '''
    uj = orm_findall(UnprocessedJob)
    return [ u.jobid for u in uj ]

@db_session
def comparable_job_partitions(jobs, matching_keys = ['exp_name', 'exp_component']):
    '''
    Given a non-empty list of job ids, the function returns a
    a list of lists, where each sub-list is of the form:
    [(val1, val2,..), { j1, j2,..}]
    where val1, val2.. are the values of the matching keys that jobs
    j1, j2, .. share.

    For example, suppose the following jobs have the following tags:
        685000 -> {'exp_name': 'ESM4_historical_D151', 'exp_component': 'ocean_annual_rho2_1x1deg', 
'exp_time': '18840101', 'atm_res': 'c96l49', 'ocn_res': '0.5l75', 'script_name': 'ESM4_historical_D151_oce
an_annual_rho2_1x1deg_18840101'}
        685003 -> {'exp_name': 'ESM4_historical_D151', 'exp_component': 'ocean_cobalt_fdet_100', 'exp_time': '18840101', 'atm_res': 'c96l49', 'ocn_res': '0.5l75', 'script_name': 'ESM4_historical_D151_ocean_cobalt_fdet_100_18840101'}
        And 625151, 627907, 633114, 629322, 685001  share the tag:
        {u'ocn_res': u'0.5l75', u'atm_res': u'c96l49', u'exp_component': u'ocean_annual_z_1x1deg', u'exp_name': u'ESM4_historical_D151'}`. The difference is only that they have different values for `('exp_time', 'script_name')
    
    Then calling comparable_job_partitions(['625151', '627907', '633114', '629322', '685001', '685000', '685003'])
    returns:
        [
          (('ESM4_historical_D151', 'ocean_annual_z_1x1deg'), { '625151', '627907', '633114', '629322', '685001'} ),
          (('ESM4_historical_D151', 'ocean_annual_rho2_1x1deg'), { '685000' }),
          (('ESM4_historical_D151',  'ocean_cobalt_fdet_100'), {'685003'})
        ]

    The default keys that require a match are 'exp_name' and 'exp_component'.
    The top-level list is ordered in decreasing cardinality of number of jobs. 
    '''
    d = {}
    jobs = orm_jobs_col(jobs)
    # logger.info('doing a comparable_job_partitions on {0} jobs'.format(jobs.count()))
    for j in jobs:
        tag = j.tags
        search_tuple = tuple([tag.get(k, '') for k in matching_keys])
        if search_tuple in d:
            d[search_tuple].append(j.jobid)
        else:
            d[search_tuple] = [j.jobid]
    # now assemble the dict into a list of tuples ordered by decreasing 
    # job count
    l = []
    for k in d.keys():
        l.append((k, d[k]))

    # sort the list in desc. order of cumulative job duration for the component
    # v[1] is the list of jobids of a component
    return sorted(l, key = lambda v: sum([Job[jobid].duration for jobid in v[1]]), reverse=True)

def are_jobs_comparable(jobs, matching_keys = ['exp_name', 'exp_component']):
    '''
    Returns True if *all* the supplied jobs are comparable. IOW, they share
    the same values for *all* the keys specified in matching_keys. Returns
    False otherwise.

    Example:
    >>> eq.are_jobs_comparable(['625151', '627907', '633114', '629322', '685001', '685000', '685003'])
    INFO:epmt_query:doing a comparable_job_partitions on 7 jobs
    False
    >>> eq.are_jobs_comparable(['625151', '627907', '633114', '629322', '685001'])
    INFO:epmt_query:doing a comparable_job_partitions on 5 jobs
    True
    '''
    return (len(comparable_job_partitions(jobs, matching_keys)) == 1)

def _warn_incomparable_jobs(jobs):
    jobs = orm_jobs_col(jobs)
    if not are_jobs_comparable(jobs):
        msg = 'The jobs do not share identical tag values for "exp_name" and "exp_component"'
        from sys import stderr
        logger.warning(msg)
        print('WARNING:', msg, file=stderr)
        for j in jobs:
            print('   ',j.jobid, j.tags.get('exp_name'), j.tags.get('exp_component'), file=stderr)


def _empty_collection_check(col):
    if (not(orm_is_query(col))) and (type(col) != pd.DataFrame) and (col in [[], '', None]):
        msg = 'You need to specify a non-empty collection as a parameter'
        logger.warning(msg)
        raise ValueError(msg)

@db_session
def compute_process_trees(jobs):
    '''
    Compute process trees for specified jobs.

    It is safe to call this function on jobs that already have process trees
    computed as they will just be skipped.
    '''
    from epmt_job import mk_process_tree
    jobs = orm_jobs_col(jobs)
    for j in jobs:
        mk_process_tree(j)


@db_session
def procs_histogram(jobs, attr = 'exename'):
    '''
    Gets a processes histogram for a collection of jobs

    jobs: collection of one or more jobs or jobids
    attr: the attribute from the process model that is the basis of
          the histogram. Defaults to 'exename'

    RETURNS: A dictionary of the form:
             { 'bash': 1256, 'cmp': 10, ... }
            where the key is a process executable and its value is the number
            of the times the executable was executed.
    '''
    logger = getLogger(__name__)  # you can use other name
    procs_hist = {}
    procs = get_procs(jobs, fmt='orm')
    logger.debug('{} processes found'.format(procs.count()))
    for p in procs:
        attr_val = getattr(p, attr)
        procs_hist[attr_val] = procs_hist.get(attr_val, 0) + 1
    return procs_hist

def procs_set(jobs, attr = 'exename'):
    '''
    Gets the set of unique values of attributes for the collection of jobs
    '''
    phist = procs_histogram(jobs, attr)
    return sorted(phist.keys())

@db_session
def add_features_df(jobs_df, features = [procs_histogram, procs_set], key = 'jobid'):
    '''
    Includes columns for synthetic metrics such as process histogram, 
    processes set and returns a new dataframe with the added columns.

    jobs_df: Input dataframe (will not be modified)

    features: List of callables. Each callable will be called with the
             value of "key" to compute the metric value for the row.

        key: The dataframe column to use to get value that will be
             passed as an argument to each of the callables

    RETURNS: (df, added_features), where

                df: A new dataframe, which will contain the columns from
                    jobs_df, alongwith new columns (one for each callable,
                    whose names are derived from the callables)
    added_features: List of new features added to dataframe

    EXAMPLES:

    >>> jobs_df = eq.get_jobs(['625151', '627907', '629322', '633114', '675992', '680163', '685001', '691209', '693129'], fmt='pandas')
    >>> new_df, added_features = eq.add_features_df(jobs_df) 
    >>> added_features
    ['procs_histogram', 'procs_set']
    >>> new_df
                      created_at  ...                                          procs_set
    0 2020-03-17 12:57:54.464202  ...  [TAVG.exe, arch, basename, bash, cat, chmod, c...
    1 2020-03-17 12:58:03.451079  ...  [TAVG.exe, arch, basename, bash, cat, chmod, c...
    2 2020-03-17 12:58:06.245651  ...  [TAVG.exe, arch, basename, bash, cat, chmod, c...
    3 2020-03-17 12:58:09.038631  ...  [TAVG.exe, arch, basename, bash, cat, chmod, c...
    4 2020-03-17 12:58:11.850036  ...  [TAVG.exe, arch, basename, bash, cat, chmod, c...
    5 2020-03-17 12:58:14.622092  ...  [TAVG.exe, arch, basename, bash, cat, chmod, c...
    6 2020-03-17 12:58:17.418585  ...  [TAVG.exe, arch, basename, bash, cat, chmod, c...
    7 2020-03-17 12:58:20.212817  ...  [TAVG.exe, arch, basename, bash, cat, chmod, c...
    8 2020-03-17 12:58:23.041036  ...  [TAVG.exe, arch, basename, bash, cat, chmod, c...
    
    [9 rows x 46 columns]
    >>> new_df[added_features]
                                         procs_histogram                                          procs_set
    0  {'tcsh': 4056, 'perl': 296, 'bash': 330, 'grep...  [TAVG.exe, arch, basename, bash, cat, chmod, c...
    1  {'tcsh': 1099, 'perl': 101, 'bash': 100, 'grep...  [TAVG.exe, arch, basename, bash, cat, chmod, c...
    2  {'arch': 46, 'grid-proxy-info': 71, 'which': 4...  [TAVG.exe, arch, basename, bash, cat, chmod, c...
    3  {'id': 6, 'bash': 100, 'date': 30, 'modulecmd'...  [TAVG.exe, arch, basename, bash, cat, chmod, c...
    4  {'tcsh': 1099, 'perl': 101, 'bash': 100, 'grep...  [TAVG.exe, arch, basename, bash, cat, chmod, c...
    5  {'rm': 197, 'cut': 240, 'du': 7, 'date': 30, '...  [TAVG.exe, arch, basename, bash, cat, chmod, c...
    6  {'tcsh': 1109, 'perl': 102, 'bash': 100, 'grep...  [TAVG.exe, arch, basename, bash, cat, chmod, c...
    7  {'tcsh': 1099, 'perl': 101, 'bash': 100, 'grep...  [TAVG.exe, arch, basename, bash, cat, chmod, c...
    8  {'mv': 118, 'perl': 101, 'globus-url-copy': 76...  [TAVG.exe, arch, basename, bash, cat, chmod, c...
    
    '''
    logger = getLogger(__name__)  # you can use other name
    out_df = jobs_df.copy()
    keys = list(jobs_df[key].values)
    added_features = []
    for c in features:
        out_df[c.__name__] = [ c(k) for k in keys ]
        added_features.append(c.__name__)
    logger.info('Added features: {}'.format(added_features))
    return out_df, added_features

def get_features(jobs):
    '''
    Returns the union of features across the input jobs.

       jobs: Collection of jobs

    RETURNS: The sorted list of features across the jobs. 

      NOTES: Blacklisted features (in settings) will be removed
             from the returned list.

   EXAMPLES:

     >>> eq.get_features(jobs)
     ['PERF_COUNT_SW_CPU_CLOCK', 'cancelled_write_bytes', 'cpu_time', 'delayacct_blkio_time', 'duration',  'exitcode', 'guest_time', 'inblock', 'invol_ctxsw', 'majflt', 'minflt', 'num_procs', 'num_threads', 'outblock', 'processor', 'rchar', 'rdtsc_duration', 'read_bytes', 'rssmax', 'submit', 'syscr', 'syscw', 'systemtime', 'time_oncpu', 'time_waiting', 'timeslices', 'updated_at', 'usertime', 'vol_ctxsw', 'wchar', 'write_bytes']

    '''
    df = get_jobs(jobs, fmt='pandas')
    all_cols = set(df.columns.values)
    return sorted(all_cols - set(settings.outlier_features_blacklist))


@db_session
def is_job_post_processed(job):
    '''
    Returns True if the post-processing pipeline has been
    run on the job. False otherwise.

      job: jobid or ORM job object. The job MUST be in the database.

    '''
    if type(job) == str:
        job = Job[job]
    # only processed jobs have this set
    info_dict = job.info_dict or {}
    # we retain the j.proc_sums check to retain backward compatibility
    return ((info_dict.get('post_processed', 0) > 0) or (job.proc_sums != None))
