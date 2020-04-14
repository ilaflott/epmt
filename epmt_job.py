from __future__ import print_function
from os.path import basename
from os import environ
from logging import getLogger
from json import dumps, loads
from epmtlib import tag_from_string, sum_dicts, timing, dotdict, get_first_key_match, check_fix_metadata
from datetime import datetime, timedelta
from functools import reduce
import time
import pytz
import csv
from io import StringIO

logger = getLogger(__name__)  # you can use other name
import epmt_settings as settings
from orm import *

#
# Spinning cursor sequence
#from itertools import cycle
#spinner = cycle(['-', '/', '|', '\\'])

# Construct a number from the pattern

def sortKeyFunc(s):
    t = basename(s)
# if this changes we must adjust this
#    assert settings.input_pattern == "papiex-[0-9]*-[0-9]*.csv"
# skip papiex- and .csv
    t = t[7:-4]
# append instance number 
    t2 = t.split("-")
    return int(t2[0]+t2[1])

def create_job(jobid,user):
    logger = getLogger(__name__)  # you can use other name
    job = orm_get(Job, jobid)
    if job is None:
        logger.info("Creating job %s",jobid)
        job = orm_create(Job, jobid=jobid,user=user)
    else:
        logger.info("Job %s (at %s) is already in the database",job.jobid,job.start)
        return None
    return job

##	metadata['job_pl_id'] = global_job_id
##	metadata['job_pl_scriptname'] = global_job_scriptname
##	metadata['job_pl_jobname'] = global_job_name
##	metadata['job_pl_from_batch'] = from_batch
#	metadata['job_pl_hostname'] = gethostname()
#	metadata['job_pl_username'] = global_job_username
#	metadata['job_pl_groupnames'] = global_job_groupnames
#	metadata['job_pl_env_len'] = len(env)
#	metadata['job_pl_env'] = env
#	metadata['job_pl_submit'] = datetime.now()
#	metadata['job_pl_start'] = ts
#	metadata['job_el_env_changes_len'] = len(env)
#	metadata['job_el_env_changes'] = env
#	metadata['job_el_stop'] = ts
#	metadata['job_el_from_batch'] = from_batch
#	metadata['job_el_status'] = status
                    
created_hosts = {}
# Rather than using this function directly, please use
# lookup_or_create_host_safe, as that handles a race condition
# when using concurrent submits
def lookup_or_create_host(hostname):
    logger = getLogger(__name__)  # you can use other name
    host = created_hosts.get(hostname)
    if host:
        # sometimes we may have cached a host entry that's been invalidated 
        # in the session cache. In such a case, we need to purge it
        try:
            host.name
        except:
            del created_hosts[hostname]
            host = None

    if host is None:
        host = orm_get(Host, hostname)
        
    if host is None:
        host = orm_create(Host, name=hostname)
        logger.info("Created host %s",hostname)
        # for sqlalchemy the created_hosts map is crucial for boosting performance
        # However with Pony we end up caching objects from different db_sessions
        # and so we don't want use our create_hosts map with Pony
        if settings.orm == 'sqlalchemy':
            created_hosts[hostname] = host
    assert(host.name == hostname)
    return host


# This function handles a race condition when submitting jobs using
# multiple processes
def lookup_or_create_host_safe(hostname):
    from sqlalchemy import exc
    try:
        h = lookup_or_create_host(hostname)
    except exc.IntegrityError:
        # The insert failed due to a concurrent transaction  
        Session.rollback()
        # the host must exist now
        h = lookup_or_create_host(hostname)
    return h

def lookup_or_create_user(username):
    logger = getLogger(__name__)  # you can use other name
    user = orm_get_or_create(User, name = username)
    # user = orm_get(User, username)
    # if user is None:
    #     logger.info("Creating user %s",username)
    #     user = orm_create(User, name=username)
    return user


# This is a generator function that will yield
# the next process dataframe from the collated file dataframe.
# It uses the numtids field to figure out where the process dataframe ends
# def get_process_df(df):
#     row = 0
#     nrows = df.shape[0]
#     while (row < nrows):
#         try:
#             thr_count = int(df['numtids'][row])
#         except Exception as e:
#             logger.error("%s", e)
#             logger.error("invalid or no value set for numtids in dataframe at index %d", row)
#             return
#         if (thr_count < 1):
#             logger.error('invalid value({0}) set for numtids in dataframe at index {1}'.format(thr_count, row))
#             return
#         # now yield a dataframe from df[row ... row+thr_count]
#         # make sure the yielded dataframe has it's index reset to 0
#         yield df[row:row+thr_count].reset_index(drop=True)
#         # advance row pointer
#         row += thr_count


def get_proc_rows(csvfile, skiprows = 0):
    if skiprows > 0:
        err_msg = 'Do not know how to handle a non-zero value for skiprows while reading CSV file'
        logger.error(err_msg)
        raise ValueError(err_msg)

    reader = csv.DictReader(csvfile, escapechar='\\')
    # ordinarily the line below would not be a good idea,
    # however, we are dealing with small CSV files so a gulp
    # of the entire dataset isn't expensive 
    rows = list(reader)

    # use int as the default type for non-empty, non-string entities
    non_numeric_keys = set(['exename', 'path', 'args', 'tags', 'hostname'])
    for r in rows:
        for k in r.keys():
            if (not (k in non_numeric_keys)) and r[k]:
                r[k] = int(r[k])

    nrows = len(rows)
    row_num = 0
    while (row_num < nrows):
        row = rows[row_num]
        try:
            thr_count = int(row['numtids'])
        except Exception as e:
            logger.error("%s", e)
            logger.error("invalid or no value set for numtids in dataframe at index %d", row_num)
            return
        if (thr_count < 1):
            logger.error('invalid value({0}) set for numtids in dataframe at index {1}'.format(thr_count, row_num))
            return
        # now yield a dataframe from df[row ... row+thr_count]
        # make sure the yielded dataframe has it's index reset to 0
        yield (rows[row_num:row_num+thr_count], row_num, nrows)
        # advance row pointer
        row_num += thr_count


# 'proc' is a list of dicts, where each list item is a 
# a dictionary containing data for a single thread
# The first list item (thread 0) is special in that it has values for fields pertaining
# to the process such as 'exename', 'args', etc. The other threads
# may not have process fields set.
def load_process_from_dictlist(proc, host, j, u, settings, profile):
    from pandas import Timestamp
    logger = getLogger(__name__)  # you can use other name

    hostname = proc[0].get('hostname', '')
    if hostname:
        if (host is None) or (host.name != hostname):
            logger.warning('using hostname as set in papiex data: {}'.format(hostname))
            host = lookup_or_create_host_safe(hostname)

    _t = time.time()
    try:
        if settings.bulk_insert:
            # we use dotdict as thin-wrapper around dict so we can use the dot syntax
            # of objects
            p = dotdict({'host_id': host.name, 'jobid': j.jobid, 'user_id': u.name})
            for key in ('exename', 'args', 'path'):
                p[key] = proc[0][key]
            for key in ('pid', 'ppid', 'pgid', 'sid', 'generation'):
                p[key] = int(proc[0][key])
        else:
            p = orm_create(Process, 
                           exename=proc[0]['exename'],
                           args=proc[0]['args'],
                           path=proc[0]['path'],
                           pid=int(proc[0]['pid']),
                           ppid=int(proc[0]['ppid']),
                           pgid=int(proc[0]['pgid']),
                           sid=int(proc[0]['sid']),
                           gen=int(proc[0]['generation']),
                           host=host,
                           job=j,
                           user=u)

    except Exception as e:
        logger.error("%s",e)
        logger.error("Corrupted CSV or invalid input type");
        raise ValueError('Corrupted CSV or invalid input type')
    profile.load_process.init += time.time() - _t

    _t = time.time()
    p.exitcode = int(proc[0]['exitcode'])
    p.numtids = len(proc)
    try:
        # FIX: Is it safe to assume that thread 0 has the lowest start time
        # and the highest end time?
        earliest_thread_start = Timestamp(int(proc[0]['start']), unit='us')
        latest_thread_finish = Timestamp(int(proc[0]['end']), unit='us')
        p.start = earliest_thread_start.to_pydatetime().replace(tzinfo = pytz.utc)
        p.end = latest_thread_finish.to_pydatetime().replace(tzinfo = pytz.utc)
        p.duration = float((latest_thread_finish - earliest_thread_start).total_seconds())*float(1000000)
    except Exception as e:
        logger.error("%s",e)
        logger.error("missing or invalid value for thread start/end time");
    profile.load_process.misc += time.time() - _t

    # We have coupled the operation below with a later df.drop to save time.
    # remove per-process fields from the threads dataframe
    # df.drop(labels=settings.per_process_fields, axis=1, inplace=True, errors = 'ignore')

    # convert the threads dataframe to a json
    # using the 'split' argument creates a json of the form:
    # { columns: ['exename', 'path', args',...], data: [['tcsh', '/bin/tcsh'..], [..]}
    # thus it preserves the column order. Remember when reading the json
    # into a dataframe, do it as:
    #
    #   df = pd.read_json(p.threads_df, orient='split')
    #
    # where 'p' is a Process object
    #
    # We pass metric_sums as a python dictionary to Pony so we can do
    # complex queries in Pony using metrics in the 'metric_sums' dict.
    _t = time.time()
    #p.threads_df = df.to_json(orient='split')
    #p.threads_df = {'columns': list(proc[0].keys()), 'data':[]}
    #for thr in proc:
    #    p.threads_df['data'].append(list(thr.values()))
    p.threads_df = proc
    profile.load_process.to_json += time.time() - _t


    _t = time.time()
    tags = proc[0].get('tags')
    if tags:
        p.tags = tag_from_string(tags)
    profile.load_process.proc_tags += time.time() - _t

    # compute sums for each column, but skip ones that we know should not be summed
    # we then convert the pandas series of sums to a Python dict
    # df.drop(labels=settings.skip_for_thread_sums, axis=1).sum(axis=0).to_dict()
    # saving the json to the database:
    # exception:    raise TypeError(repr(o) + " is not JSON serializable")
    # So, instead we use this workaround:
    # df_summed = df.drop(labels=settings.skip_for_thread_sums+settings.per_process_fields, axis=1).sum(axis=0)
    # if sys.version_info > (3,0):
    #     json_ms = df_summed.to_json()
    #     thread_metric_sums = loads(json_ms)
    # else:
    #     thread_metric_sums = df_summed.to_dict()

    # # we add a composite metric comprising of user+system time as this
    # # is needed in queries, and Pony doesn't allow operations on json fields
    # # in a Query
    # # TODO: can this be removed?
    # thread_metric_sums['user+system'] = thread_metric_sums.get('usertime', 0) + thread_metric_sums.get('systemtime', 0)

    _t = time.time()
    fields = set(proc[0].keys()) - set(settings.skip_for_thread_sums) - set(settings.per_process_fields)
    thread_metric_sums = {k: 0 for k in fields }

    for thr in proc:
        for k in fields:
            thread_metric_sums[k] += thr[k]

    p.threads_sums = thread_metric_sums

    p.cpu_time = float(thread_metric_sums['usertime'] + thread_metric_sums['systemtime'])
    profile.load_process.thread_sums += time.time() - _t

    return p
    
#
# Extract a dictionary from the rows of header on the file
#

def extract_tags_from_comment_line(jobdatafile,comment="#",tarfile=None):
    rows = 0
    retstr = None

    if tarfile:
        try:
            info = tarfile.getmember(jobdatafile)
        except KeyError:
            err_msg = 'BUG: Did not find %s in tar archive' % str(tarfile)
            logger.error(err_msg)
            raise LookupError(err_msg)
        else:
            f = tarfile.extractfile(info)
    else:
        f = open(jobdatafile,'r')
    
    line = f.readline()
    while line:
        line = line.strip()
        if len(line) == 0 or (str(line)).startswith(comment):
            if rows == 0:
                retstr = line[1:].lstrip()
            rows += 1
            line = file.readline()
        else:
            return rows, retstr

    return rows, retstr

#        for member in tar.getmembers():

#def check_experiment_in_metadata(metadata):
#    for i in ("exp_name","exp_component","exp_oname","exp_jobname"):
#        if i not in metadata:
#            return False
#    return True
#
# Load experiment
# 

# @db_session
# def ETL_ppr(metadata, jobid):
# #    if not check_experiment_in_metadata(metadata):
# #        return None
# 
#     logger.info("Creating PostProcessRun(%s,%s,%s,%s)",
#                 metadata["exp_component"],
#                 metadata["exp_name"],
#                 metadata["exp_jobname"],
#                 metadata["exp_oname"])
#     exp = PostProcessRun(component=metadata["exp_component"],
#                          name=metadata["exp_name"],
#                          jobname=metadata["exp_jobname"],
#                          oname=metadata["exp_oname"],
#                          user=Job[jobid].user,
#                          job=Job[jobid])
#     return exp

# walk up the process tree starting from the supplied ancestor
# and ensure  that every ancestor of the supplied process(proc) includes
# proc in its descendants, and proc.ancestors includes all ancestors
# We only use relations for bulk mapping as orm_add_to_collection is
# really slow if the processes are to be re-read from the DB
# relations and descendant maps are used if we do bulk inserts
def _proc_ancestors(pid_map, proc, ancestor_pid, relations = None, descendant_map = {}):
    
    if ancestor_pid in pid_map:
        proc.depth += 1
        entries = pid_map[ancestor_pid]
        if len(entries) == 1:
            # common case no hash collision
            ancestor = entries[0]
        else:
            # get the actual parent from the list of possible parent entries
            ancestor = _disambiguate_parent(entries, proc)
        if ancestor.id in descendant_map:
            descendant_map[ancestor.id].add(proc)
        else:
            descendant_map[ancestor.id] = set([proc])
        if not(relations is None):
            relations.append({'ancestor': ancestor.id, 'descendant': proc.id})
        else:
            orm_add_to_collection(ancestor.descendants, proc)

        # we don't need to do the reverse mapping (below) as that's
        # implied using the ORM backref. And if we uncomment it,
        # then sqlalchemy tries to add a duplicate record
        # orm_add_to_collection(proc.ancestors, ancestor)

        # now that we have done this node let's go to its parent
        _proc_ancestors(pid_map, proc, ancestor.ppid, relations, descendant_map)
    return (relations, descendant_map)

# Makes a pid map (a dictionary referenced by PIDs).
# Each dict entry is a list containing one or more Process
# (or dotdict if using bulk inserts) objects.
def _mk_pid_map(all_procs):
    pid_map = {}
    for p in all_procs:
        if p.pid in pid_map:
            logger.debug('handled hash collision for PID (%d) -- process execed', p.pid)
            pid_map[p.pid].append(p)
        else:
            pid_map[p.pid] = [p]
    return pid_map


# determines the actual parent of a process give a list
# of candidates whose PID matches the PPID of proc.
# proc is a dotdict or a Process object
def _disambiguate_parent(entries, proc):
    sorted_entries = sorted(entries, key = lambda p: p.start)
    for p in sorted_entries:
        if (p.end > proc.start):
            # if (p.start > proc.start):
            #     for x in sorted_entries:
            #         print(x.pid, x.ppid, x.exename, x.start, x.end)
            #     print('---')
            #     print(proc.pid, proc.ppid, proc.exename, proc.start, proc.end)
            # assert(p.start < proc.start)
            return p
    # each process has a unique parent, so we know
    # control must never come here else something's broken
    assert(False)


def _create_process_tree(pid_map):
    logger = getLogger(__name__)  # you can use other name
    logger.info("  creating process tree..")
    for (pid, procs) in pid_map.items():
        for proc in procs:
            ppid = proc.ppid
            if ppid in pid_map:
                entries = pid_map[ppid]
                if len(entries) == 1:
                    # common case no hash collision
                    parent = entries[0]
                else:
                    # the process must have execed so we have
                    # multiple records for the PID.
                    for e in entries: assert(e.pid == ppid)
                    parent = _disambiguate_parent(entries, proc)
                proc.parent = parent
                # commented out line below as it's automatically
                # implied by the proc.parent assignment above.
                # If we uncomment it, then on sqlalchemy, each
                # parent will have duplicate nodes for each child.
                # orm_add_to_collection(parent.children, proc)

    logger.debug('    creating ancestor/descendant relations..')
    r = [] if settings.bulk_insert else None
    # descendants map
    desc_map = {}
    for (pid, procs) in pid_map.items():
        for proc in procs:
            ppid = proc.ppid
            proc.depth = 0
            (r, desc_map) = _proc_ancestors(pid_map, proc, ppid, r, desc_map)

    # r will only be non-empty if we are doing bulk-inserts
    if r:
        logger.debug("    doing bulk insert of ancestor/descendant relations")
        t = Base.metadata.tables['ancestor_descendant_associations']
        thr_data.engine.execute(t.insert(), r)
    return desc_map

def is_process_tree_computed(j):
    return bool(j.info_dict.get('process_tree'))

# High-level function to create and persist a process tree
# It will also compute and save process inclusive_cpu_times.
# You should be using this function instead of directly calling
# _create_process_tree.
# 'all_procs' and 'pid_map' are optional and if supplied
# will reduce processing time.
@db_session
def mk_process_tree(j, all_procs = None, pid_map = None):
    if type(j) == str:
        j = Job[j]
    info_dict = j.info_dict.copy()
    if info_dict.get('process_tree'):
        # logger.debug('Process tree already exists. Skipping mk_process_tree')
        return
    logger.info('computing process tree for job %s', j.jobid)
    if all_procs is None:
        _all_procs_t0 = time.time()
        all_procs = []
        for p in j.processes:
            all_procs.append(p)
        logger.debug('  re-populating %d processes took: %2.5f sec', len(all_procs), time.time() - _all_procs_t0)

    if (pid_map is None):
        _pid_t0 = time.time()
        pid_map = _mk_pid_map(all_procs)
        logger.debug("  recreating pid_map took: %2.5f sec", time.time() - _pid_t0)

    _t1 = time.time()
    desc_map = _create_process_tree(pid_map)
    _t2 = time.time()
    # make sure the inane ORM can understand that we are
    # updating info_dict
    info_dict.update({ 'process_tree': 1 })
    j.info_dict = info_dict

    logger.debug('  process tree took: %2.5f sec', _t2 - _t1)
    # computing process inclusive times
    for proc in all_procs:
        if settings.bulk_insert:
            # in bulk inserts, we cannnot rely on process.descendants to be
            # available, so we use a descendants map created during the
            # process tree creation step
            proc_descendants = desc_map.get(proc.id, set())
            proc.inclusive_cpu_time = float(proc.cpu_time + sum([p.cpu_time for p in proc_descendants]))
        else:
            proc.inclusive_cpu_time = float(proc.cpu_time + orm_sum_attribute(proc.descendants, 'cpu_time'))
    _t3 = time.time()
    logger.debug('  proc inclusive. cpu times computation took: %2.5f sec', _t3 - _t2)
    orm_commit()
    logger.debug('  commit time : %2.5f sec', time.time() - _t3)
    return

# This method will compute sums across processes/threads of a job,
# and do post-processing on tags. It will also call _create_process_tree
# to create process tree.
#
# The function is tolerant to missing datastructures for all_tags
# all_procs and pid_map. If any of them are missing, it will 
# build them by using the data in the database/ORM.
# 
@timing
def post_process_job(j, all_tags = None, all_procs = None, pid_map = None, update_unprocessed_jobs_table = True):
    logger = getLogger(__name__)  # you can use other name
    if type(j) == str:
        j = Job[j]
    if j.proc_sums:
        logger.warning('skipped processing jobid {0} as it is not unprocessed'.format(j.jobid))
        return False
    logger.info("Starting post-process of job..")
    proc_sums = {}

    _t0 = time.time()

    if all_tags == None:
        logger.info("  recreating all_tags..")
        all_tags = set()
        # we need to read the tags from the processes
        for p in j.processes:
            if p.tags:
                all_tags.add(dumps(p.tags, sort_keys=True))

    # Add sum of tags to job
    if all_tags:
        logger.info("  found %d distinct sets of process tags",len(all_tags))
        # convert each of the pickled tags back into a dict
        proc_sums['all_proc_tags'] = [ loads(t) for t in sorted(all_tags) ]
    else:
        logger.debug('  no process tags found in th entire job')
        proc_sums['all_proc_tags'] = []

    logger.debug('  tag processing took: %2.5f sec', time.time() - _t0)

    if all_procs is None:
        _all_procs_t0 = time.time()
        all_procs = []
        for p in j.processes:
            all_procs.append(p)
        logger.debug('  re-populating %d processes took: %2.5f sec', len(all_procs), time.time() - _all_procs_t0)

    # Add all processes to job and compute process totals to add to
    # job.proc_sums field
    nthreads = 0
    threads_sums_across_procs = {}
    if all_procs:
        logger.info("  computing thread sums across job processes..")
        _t2 = time.time()
        hosts = set()
        for proc in all_procs:
            if settings.bulk_insert:
                hosts.add(proc.host_id)
            else:
                hosts.add(proc.host)
            nthreads += proc.numtids
            threads_sums_across_procs = sum_dicts(threads_sums_across_procs, proc.threads_sums)
        logger.info("  job contains %d processes (%d threads)",len(all_procs), nthreads)
        _t3 = time.time()
        logger.debug('  thread sums calculation took: %2.5f sec', _t3 - _t2)
        if settings.bulk_insert:
            t = Base.metadata.tables['host_job_associations']
            thr_data.engine.execute(t.insert(), [ { 'jobid': j.jobid, 'hostname': h } for h in hosts])
        else:
            j.hosts = list(hosts)
        _t4 = time.time()
        logger.debug('  adding %d host(s) to job took: %2.5f sec', len(hosts), _t4 - _t3)

        # we MUST NOT add all_procs to j.processes below
        # as we already associated the process with the job
        # when we created the process. The ORM automatically does the backref.
        # In particular, in sqlalchemy, uncommenting the line below creates 
        # duplicate bindings.
        # orm_add_to_collection(j.processes, all_procs)

    _t4 = time.time()
    proc_sums['num_procs'] = len(all_procs)
    proc_sums['num_threads'] = nthreads
    # merge the threads sums across all processes in the job.proc_sums dict
    for (k, v) in threads_sums_across_procs.items():
        proc_sums[k] = v
    j.proc_sums = proc_sums
    # we need to create a copy so the ORM actually saves the modifications
    # Merely updating a dict often confuses the ORM and the changes are lost
    info_dict = dict.copy(j.info_dict or {})
    info_dict['post_processed'] = 1
    j.info_dict = info_dict
    _t5 = time.time()
    logger.debug('  proc_sums calculation took: %2.5f sec', _t5 - _t4)
    logger.info('marked job as post-processed')

    if not settings.lazy_compute_process_tree:
        mk_process_tree(j, all_procs)

    # The calculation below has been moved to before post-processing
    #
    # the cpu time for a job is the sum of the exclusive times
    # of all processes in the job
    # We use list-comprehension and aggregation over slower ORM ops
    ### j.cpu_time = orm_sum_attribute(j.processes, 'cpu_time')
    # j.cpu_time = sum([p.cpu_time for p in all_procs])
    # _t6 = time.time()
    # logger.debug('job cpu_time calculation took: %2.5f sec', _t6 - _t5)

    # now mark the job as processed if it was previously marked otherwise
    # for now, only sqlalchemy supports post-processing in a separate phase
    # update_unprocessed_jobs_table option is used to speed up operations if the 
    # job has been just created. In this case, we know the job doesn't
    # already exist in the UnprocessedJobs table. This saves us a lookup
    # which ordinarily should've been cheap, but because we haven't yet 
    # done a commit/flush to the DB, the lookup appears as expensive and
    # makes the overall post-processing function appear costly, even though
    # it's just the cost of the db commit/flush
    # For delayed post-processing, the lookup isn't expensive as the commit
    # has already happened. Note this optimization doesn't really save any
    # time. It just fixes the profiling accounting and makes the commit
    # time appear under the commit head, and not in post processing
    if update_unprocessed_jobs_table:
        if settings.orm == 'sqlalchemy':
            _t6 = time.time()
            u = orm_get(UnprocessedJob, pk=j.jobid)
            if u:
                orm_delete(u)
                logger.info('  marking job as processed in database')
                orm_commit()
            logger.debug('  checking/updating unprocessed jobs table (includes implicit commit) took: %2.5f sec', time.time() - _t6)
    return True


# This function takes as input raw metadata from the start/stop and produces
# extended dictionary of additional fields used in the ETL. This created
# structure is never stored and just used for information exchange

# The following raw fields are stored during start/stop
#    metadata['job_pl_id'] = jobid
#    metadata['job_pl_hostname'] = gethostname()
#    metadata['job_pl_start_ts'] = ts
#    metadata['job_pl_submit_ts'] = submit_ts
#    metadata['job_pl_env'] = start_env
#    metadata['job_el_env'] = stop_env
#    metadata['job_el_stop_ts'] = ts
#    metadata['job_el_from_batch'] = from_batch
#    metadata['job_el_exitcode'] = exitcode
#    metadata['job_el_reason'] = reason

@db_session
def ETL_job_dict(raw_metadata, filedict, settings, tarfile=None):
    logger = getLogger(__name__)  # you can use other name
    job_init_start_time = time.time()
# Synthesize what we need
    # it's safe and fast to call the check_fix_metadata
    # it will not waste time re-checking (since it marks the metadata as checked)
    metadata = check_fix_metadata(raw_metadata) 
    if metadata is False:
        return (False, 'Error: Could not get valid metadata')
    job_status = {}
    if metadata.get('job_pl_scriptname'):
        job_status['script_name'] = metadata['job_pl_scriptname']
    if metadata.get('job_pl_script'):
        job_status['script'] = metadata['job_pl_script']
    if metadata.get('job_el_stdout'):
        job_status['stdout'] = metadata['job_el_stdout']
    if metadata.get('job_el_stderr'):
        job_status['stderr'] = metadata['job_el_stderr']
    if metadata.get('job_el_exitcode') is not None:
        job_status['exit_code'] = metadata['job_el_exitcode']
    if metadata.get('job_el_reason'):
        job_status['exit_reason'] = metadata['job_el_reason']

    env_dict = metadata['job_pl_env']
    # sometimes the post-processing script's full path is to be found here
    if env_dict.get('pp_script'):
        job_status['script_path'] = env_dict.get('pp_script')

# Fields used in this function
    jobid = metadata['job_pl_id']
    username = metadata['job_pl_username']
    start_ts = metadata['job_pl_start_ts']
    stop_ts = metadata['job_el_stop_ts']
    submit_ts = metadata['job_pl_submit_ts']
    if not start_ts.tzinfo:
        tz_str = get_first_key_match(env_dict, 'TZ', 'TIMEZONE') or get_first_key_match(environ, 'EPMT_TZ') or 'US/Eastern'
        logger.debug('timezone could not be auto-detected, assuming {0}'.format(tz_str))
        tz_default = pytz.timezone(tz_str)
        start_ts = tz_default.localize(start_ts)
        stop_ts = tz_default.localize(stop_ts)
        submit_ts = tz_default.localize(submit_ts)
    else:
        tz_default = start_ts.tzinfo
        logger.debug('timezone auto-detected: {0}'.format(tz_default))
    logger.info('Job start: {0}'.format(start_ts))
    logger.info('Job finish: {0}'.format(stop_ts))
    jobname = metadata['job_jobname']
    exitcode = metadata['job_el_exitcode']
    env_changes_dict = metadata['job_env_changes']
    job_tags = metadata['job_tags']
    annotations = metadata.get('job_annotations', {})
    if annotations:
        logger.info('Job annotations: {0}'.format(annotations))

    # sometimes script name is to be found in the job tags
    if (job_status.get('script_name') is None) and job_tags and job_tags.get('script_name'):
        job_status['script_name'] = job_tags.get('script_name')

#    info_dict = metadata['job_pl_from_batch'] # end batch also

    logger.info("Processing job id %s",jobid)

    # Initialize elements used in compute
    then = datetime.now()
    csvt = timedelta()
    earliest_process = datetime.utcnow().replace(tzinfo=pytz.utc)
    latest_process = datetime.fromtimestamp(0).replace(tzinfo=pytz.utc)

#    stdout.write('-')
# Hostname, job, metricname objects
# Iterate over hosts

    logger.debug("Iterating over %d hosts for job ID %s, user %s...",len(filedict.keys()),jobid,username)

#
# Create user and job object
#
    from sqlalchemy import exc
    try:
        u = lookup_or_create_user(username)
    except exc.IntegrityError:
        # The insert failed due to a concurrent transaction  
        Session.rollback()
        # the user must exist now
        u = lookup_or_create_user(username)
    j = create_job(jobid,u)
    if not j: # FIX! We might have leaked a username to the database here
        return (None, 'Job already in database')
    j.jobname = jobname
    j.exitcode = exitcode
    j.annotations = annotations    
# fix below
    j.env_dict = env_dict
    j.env_changes_dict = env_changes_dict
    job_init_fini_time = time.time()
    logger.debug('job init took: %2.5f sec', job_init_fini_time - job_init_start_time)

    didsomething = False
    all_tags = set()
    all_procs = []
    root_proc = None

    # a pid_map is used to create the process graph
    pid_map = {}  # maps pids to process objects

    file_io_time = 0
    df_process_time = 0
    proc_tag_process_time = 0
    load_process_from_df_time = 0
    proc_misc_time = 0
    profile = dotdict()
    profile.load_process = dotdict({'init': 0, 'misc': 0, 'proc_tags': 0, 'thread_sums': 0, 'to_json': 0})

    for hostname, files in filedict.items():
        if hostname == "unknown":
            logger.warning('could not determine hostname from filedict, picking it from metadata instead')
            hostname = metadata.get('job_pl_hostname', '')
            if not hostname:
                logger.warning('could not determine hostname from metadata either')
        logger.debug("Processing host %s",hostname)
        h = None
        if hostname:
            h = lookup_or_create_host_safe(hostname)
        cntmax = len(files)
        cnt = 0
        nrecs = 0
        fileno = 0
        csv = datetime.now()
        for f in files:
            fileno += 1
            _file_io_start_ts = time.time()
            logger.debug("Processing file %s (%d of %d)",f, fileno, cntmax)
#
#            stdout.write('\b')            # erase the last written char
#            stdout.write(spinner.next())  # write the next character
#            stdout.flush()                # flush stdout buffer (actual character display)
#
# We need rows to skip
# oldproctag (after comment char) is outdated as a process tag but kept for posterities sake
            skiprows,oldproctag = extract_tags_from_comment_line(f,tarfile=tarfile)
            logger.debug("%s had %d comment rows, oldproctags %s",f,skiprows,oldproctag)

            if tarfile:
                info = tarfile.getmember(f)
                flo = tarfile.extractfile(info)
            else:
                flo = f

            csv_file = StringIO(flo.read().decode('utf8'))
                
            # from pandas import read_csv
            # collated_df = read_csv(flo,
            #                        sep=",",
            #                        #dtype=dtype_dic, 
            #                        converters=conv_dic,
            #                        skiprows=rows, escapechar='\\')
            file_io_time += time.time() - _file_io_start_ts
            # if collated_df.empty:
            #     logger.error("Something wrong with file %s, readcsv returned empty, skipping...",f)
            #     continue


# Make Process/Thread/Metrics objects in DB
            # there are 1 or more process dataframes in the collated df
            # let's iterate over them
            _df_process_start_ts = time.time()
           
            # we ignore the second value returned by get_proc_rows
            # (rownum). The third is just a fixed value (number of
            # rows in csv). 
            for (proc, _, nrows) in get_proc_rows(csv_file, skiprows):
                _load_process_from_df_start_ts = time.time()
                p = load_process_from_dictlist(proc, h, j, u, settings, profile)
                load_process_from_df_time += time.time() - _load_process_from_df_start_ts
                if not p:
                    logger.error("Failed loading process, file %s!",f);
                    continue
# If using old version of papiex, process tags are in the comment field
                _proc_tag_start_ts = time.time()
                if not p.tags:
                    p.tags = tag_from_string(oldproctag) if oldproctag else {}

                if p.tags:
                    # pickle and add tag dictionaries to a set
                    # remember to sort_keys during the pickle!
                    all_tags.add(dumps(p.tags, sort_keys=True))
                proc_tag_process_time += time.time() - _proc_tag_start_ts

                _t = time.time()
                # We shouldn't be seeing a pid repeat in a job. 
                # Theoretically it's posssible but it would complicate the pid map a bit
                # assert(p.pid not in pid_map)
                pid_map[p.pid] = p
                all_procs.append(p)
# Compute duration of job
                if (p.start < earliest_process):
                    earliest_process = p.start
                    root_proc = p
                if (p.end > latest_process):
                    latest_process = p.end

                # correct the process start/stop times for timezone
                # start_ts and end_ts are timezone-aware datetime objects
                p.start = p.start.replace(tzinfo = pytz.utc).astimezone(tz=tz_default)
                p.end   = p.end.replace(tzinfo = pytz.utc).astimezone(tz=tz_default)
                if ((p.start < start_ts) or (p.end > stop_ts)):
                    msg = 'Corrupted CSV detected: Process ({0}, pid {1}) start/finish times ({2}, {3}) do not fall within job interval ({4}, {5}). Bailing on job ingest..'.format(p.exename, p.pid, p.start, p.end, start_ts, stop_ts)
                    logger.error(msg)
                    raise ValueError(msg)
                # save naive datetime objects in the database
                p.start = p.start.replace(tzinfo = None)
                p.end = p.end.replace(tzinfo = None)

# Debugging/    progress
                cnt += 1
                nrecs += p.numtids
                csvt = datetime.now() - csv
                if (((nrecs % 1000) == 0) or \
                    ((cntmax==1) and (nrecs == nrows)) or \
                    ((cntmax > 1) and (fileno == cntmax))):
                    if cntmax > 1:
                        # many small files each with a single process
                        logger.info("Did %d (%d/%d files)...%.2f/sec",nrecs,fileno, cntmax,nrecs/csvt.total_seconds())
                    else:
                        # collated file
                        logger.info("Did %d (%d in file)...%.2f/sec",nrecs,nrows,nrecs/csvt.total_seconds())
                    # break
                proc_misc_time += time.time() - _t

            df_process_time += time.time() - _df_process_start_ts

#
        if cnt:
            didsomething = True

#    stdout.write('\b')            # erase the last written char
    logger.debug('file I/O time took: %2.5f sec', file_io_time)
    logger.debug('process load ops took: %2.5f sec', df_process_time)
    logger.debug('  - load process from dictlist took: %2.5f sec', load_process_from_df_time)
    logger.debug('    - {0}'.format([ "%s: %2.5f sec" % (k, v)  for (k,v) in profile.load_process.items()]))
    logger.debug('  - tag processing took: %2.5f sec', proc_tag_process_time)
    logger.debug('  - proc misc. processing took: %2.5f sec', proc_misc_time)
    logger.debug('  - get_proc_rows took: %2.5f sec', df_process_time - load_process_from_df_time - proc_tag_process_time - proc_misc_time)

    if filedict:
        if not didsomething:
            logger.warning("Something went wrong in parsing CSV files")
            return (False, "Error parsing CSV")
    else:
        logger.warning("job %s, user %s, jobname %s has no CSV data",jobid,username,jobname)

    # save naive datetime objects in the database
    j.start = start_ts.replace(tzinfo=None)
    j.end = stop_ts.replace(tzinfo=None)
    j.submit = submit_ts.replace(tzinfo=None) # Wait time is start - submit and should probably be stored
    j.info_dict = {'tz': start_ts.tzinfo.tzname(None), 'status': job_status}

    d = j.end - j.start
    j.duration = int(d.total_seconds()*1000000)
    j.cpu_time = reduce(lambda c, p: c + p.cpu_time, all_procs, 0)
    # j.cpu_time = sum([p.cpu_time for p in all_procs])
    #logger.info("Earliest process start: %s",j.start)
    #logger.info("Latest process end: %s",j.end)
    logger.info("Computed duration of job: %f us, %.2f m",j.duration,j.duration/60000000)

    if root_proc:
        if root_proc.exitcode != j.exitcode:
            logger.warning('metadata shows the job exit code is {0}, but root process exit code is {1}'.format(j.exitcode, root_proc.exitcode))
        j.exitcode = root_proc.exitcode
        logger.info('job exit code (using exit code of root process): {0}'.format(j.exitcode))
    j.tags = job_tags if job_tags else {}

    if settings.bulk_insert and all_procs:
        logger.info('doing a bulk insert of {0} processes'.format(len(all_procs)))
        _b0 = time.time()
        #thr_data.engine.execute(Process.__table__.insert(), all_procs)
        Session.bulk_insert_mappings(Process, all_procs)
        logger.info('bulk insert of processes took: %2.5f sec', time.time() - _b0)

    
    if settings.post_process_job_on_ingest:
        # _post_process_start_ts = time.time()
        if settings.bulk_insert:
            # when doing bulk inserts we don't pass in all_procs
            # and pid_map as they have to be recreated using
            # ORM objects and not the dotdicts we used for bulk
            # inserts. Otherwise the calls to create_process_tree
            # will fail as they rely on relationships between the
            # orm objects, and in particular the primary IDs of the
            # processes will be NULL. We will need to commit()
            # prior to calling post_process_job so that relationships
            # such as j.processes work after the processes were
            # bulk-inserted.
            orm_commit()
            post_process_job(j, all_tags, None, None, False)
        else:
            post_process_job(j, all_tags, all_procs, pid_map, False)
        # logger.debug('post process job took: %2.5f sec', time.time() - _post_process_start_ts)
    else:
        orm_create(UnprocessedJob, jobid=j.jobid)
        logger.info('Skipped post-processing and marked job as **UNPROCESSED**')

    logger.info("Committing job to database..")
    _c0 = time.time()
    orm_commit()
    logger.debug("commit time: %2.5f sec", time.time() - _c0)
    now = datetime.now()
    logger.info("Staged import of %d processes took %s, %f processes/sec",
                len(all_procs), now - then,len(all_procs)/float((now-then).total_seconds()))
    print("Imported successfully - job:",jobid,"processes:",len(all_procs),"rate:",len(all_procs)/float((now-then).total_seconds()))
    return (True, 'Import successful', (j.jobid, len(all_procs)))

#
# We should remove below here
#
# if (__name__ == "__main__"):
#     import argparse
#     from epmt_cmds import read_job_metadata, dump_settings
# 
#     parser=argparse.ArgumentParser(description="Load a job into the database.\nDetailed configuration is stored in settings.py.")
# 
#     parser.add_argument('data_dir',type=str,help="Directory containing papiex data files with pattern: "+settings.input_pattern);
#     parser.add_argument('metadata_dir',nargs="?",type=str,help="Directory containing the job_metadata file, defaults to data_dir");
#     parser.add_argument('jobid',type=str,nargs="?",help="Job id, a unique integer, should match that in job_metadata file");
#     parser.add_argument('-d', '--debug',action='count',help="Increase level of verbosity/debug")
#     parser.add_argument('--drop',action='store_true',help="Drop all tables/data and recreate before import")
#     parser.add_argument('-f', '--force',action='store_true',help="Override job id in job_metadata file")
#     parser.add_argument('-n', '--dry-run',action='store_true',help="Don't touch the database");
# 
# #    parser.add_argument("-v", "--verbosity", action="count",
# #                        help="increase output verbosity")
# # parser.add_argument("-v", "--verbosity", type=int, choices=[0, 1, 2],
# #                    help="increase output verbosity")
#     args = parser.parse_args()
# 
#     if not args.debug:
#         basicConfig(level=WARNING)
#     elif args.debug == 1:
#         basicConfig(level=INFO)
#     elif args.debug >= 2:
#         basicConfig(level=DEBUG)
# 
#     if args.dry_run and args.drop:
#         logger.warning("Dry-run will still drop tables, hope you know what you are doing!")
# 
#     if not args.data_dir.endswith("/"):
#         logger.warn("data_dir %s should have a trailing /",args.data_dir)
#         args.data_dir = args.data_dir+"/"
# 
#     if args.data_dir and not args.metadata_dir:
#         logger.info("Assuming metadata_dir is data_dir %s",args.data_dir)
#         args.metadata_dir = args.data_dir
#     elif not args.metadata_dir.endswith("/"):
#         logger.warn("metadata_dir %s should have a trailing /",args.metadata_dir)
#         args.metadata_dir = args.metadata_dir+"/"
# 
#     metadata = read_job_metadata(args.metadata_dir+"job_metadata")
# 
#     if not args.jobid:
#         args.jobid = metadata['job_pl_id']
#     elif args.jobid != metadata['job_pl_id']:
#         if not args.force:
#             msg = "Job id in metadata %s different from %s on command line, see --force",metadata['job_pl_id'],args.jobid
#             logger.error(msg)
#             exit(1)
#         else:
#             logger.warning("Forcing job id to be %s from command line",args.jobid)
#             metadata['job_pl_id'] = args.jobid
# 
#     if setup_orm_db(args.drop) == False:
#         exit(1)
# 
#     if args.dry_run:
#         logger.info("Skipping ETL...")
#     else:
#         j = ETL_job_dir(args.jobid,args.data_dir,metadata)
#         if not j:
#             exit(1)
#     exit(0)

def post_process_pending_jobs():
    '''
       This function will post-process all pending jobs that have
       not been post-processed.
       It returns the list of jobids that were post-processed.
    '''
    # we only support post-processing for SQLA at the moment
    if settings.orm != 'sqlalchemy':
        return []

    unproc_jobs = orm_findall(UnprocessedJob)
    did_process = []
    for u in unproc_jobs:
        jobid = u.jobid
        j = u.job
        logger.info('post-processing {0}'.format(jobid))
        if post_process_job(j):
            did_process.append(jobid)
    return did_process
