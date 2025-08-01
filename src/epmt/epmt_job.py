"""
EPMT job module - handles job-related data structures and operations.
"""
# from __future__ import print_function
from epmt.orm import (
    Base, Host, Job, Process, Session, UnprocessedJob, User,
    db_session, orm_add_to_collection, orm_commit, orm_create, orm_db_provider,
    orm_delete, orm_findall, orm_get, orm_get_or_create, orm_raw_sql, orm_sum_attribute
)
import epmt.epmt_settings as settings
from os.path import basename, dirname
from os import environ
from logging import getLogger
from json import dumps, loads
from epmt.epmtlib import tag_from_string, sum_dicts, timing, dotdict, get_first_key_match, check_fix_metadata, logfn
from epmt.epmt_query import is_job_post_processed
from datetime import datetime, timedelta
from functools import reduce
import time
import pytz
import csv
import sys
from io import StringIO

logger = getLogger(__name__)  # you can use other name

#
# Spinning cursor sequence
# from itertools import cycle
# spinner = cycle(['-', '/', '|', '\\'])

# Construct a number from the pattern


def sortKeyFunc(s):
    t = basename(s)
# if this changes we must adjust this
#    assert settings.input_pattern == "papiex-[0-9]*-[0-9]*.csv"
# skip papiex- and .csv
    t = t[7:-4]
# append instance number
    t2 = t.split("-")
    return int(t2[0] + t2[1])


@logfn
def create_job(jobid, user):
    # This code sucks, it should not get before create. It should properly handle the exception, rollback and restart
    job = orm_get(Job, jobid)
    if job:
        return None
    job = orm_create(Job, jobid=jobid, user=user)
    return job

# metadata['job_pl_id'] = global_job_id
# metadata['job_pl_scriptname'] = global_job_scriptname
# metadata['job_pl_jobname'] = global_job_name
# metadata['job_pl_from_batch'] = from_batch
# metadata['job_pl_hostname'] = gethostname()
# metadata['job_pl_username'] = global_job_username
# metadata['job_pl_groupnames'] = global_job_groupnames
# metadata['job_pl_env_len'] = len(env)
# metadata['job_pl_env'] = env
# metadata['job_pl_submit'] = datetime.now()
# metadata['job_pl_start'] = ts
# metadata['job_el_env_changes_len'] = len(env)
# metadata['job_el_env_changes'] = env
# metadata['job_el_stop'] = ts
# metadata['job_el_from_batch'] = from_batch
# metadata['job_el_status'] = status


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
        except BaseException:
            del created_hosts[hostname]
            host = None

    if host is None:
        host = orm_get(Host, hostname)

    if host is None:
        host = orm_create(Host, name=hostname)
        logger.info("Created host %s", hostname)
        # for sqlalchemy the created_hosts map is crucial for boosting performance
        # However with Pony we end up caching objects from different db_sessions
        # and so we don't want use our create_hosts map with Pony
        if settings.orm == 'sqlalchemy':
            created_hosts[hostname] = host
    assert (host.name == hostname)
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
    user = orm_get_or_create(User, name=username)
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


# Generator function that returns a
def get_proc_rows(csvfile, skiprows=0, fmt='1', metric_names=[]):
    from epmt.epmt_convert_csv import OUTPUT_CSV_FIELDS, OUTPUT_CSV_SEP
    # we only support two formats at present
    if fmt not in ('1', '2'):
        raise ValueError('CSV format ({}), not recognized'.format(fmt))

    if skiprows > 0:
        err_msg = 'Do not know how to handle a non-zero value for skiprows while reading CSV file'
        logger.error(err_msg)
        raise ValueError(err_msg)

    # csv v1 format has a header, for v2, we know the field names a priori
    # v2 also uses a different delimiter
    reader = csv.DictReader(
        csvfile,
        escapechar='\\') if fmt == '1' else csv.DictReader(
        csvfile,
        fieldnames=OUTPUT_CSV_FIELDS,
        delimiter=OUTPUT_CSV_SEP)

    # ordinarily the line below would not be a good idea,
    # however, we are dealing with small CSV files (less than 200k rows) so a gulp
    # of the entire dataset isn't expensive
    rows = list(reader)

    # use int as the default type for non-empty, non-string entities
    non_numeric_keys = set(['exename', 'path', 'args', 'tags', 'hostname', 'threads_df'])
    for r in rows:
        for k in r.keys():
            if (not (k in non_numeric_keys)) and r[k]:
                r[k] = int(r[k])
        if fmt == '2':
            # CSV v2 format has 'finish' instead of 'end'
            # so here we adapt to make it like v1
            r['end'] = r['finish']
            del r['finish']

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
            logger.error('invalid value({0}) set for numtids at index {1}'.format(thr_count, row_num))
            return
        if fmt == '1':
            # now yield rows from [row ... row+thr_count]
            # make sure the yielded dataframe has it's index reset to 0
            yield (rows[row_num:row_num + thr_count], row_num, nrows)
            # advance row pointer
            row_num += thr_count
        else:
            # v2 format
            # All threads are in a single row.
            # We want to expand that into multiple rows
            # First we get the threads_df array. This a flattened 1-d
            # array of metrics from *all* threads. It is a comma-separated
            # string enclosed in curly braces. We read in the array and then
            # split it into multiple rows like v1 format would expect
            thr_arr = row['threads_df'].replace('{', '').replace('}', '').split(',')
            num_metrics = len(metric_names)
            process_data = []
            for t in range(thr_count):
                thr_metrics = {metric_names[i]: int(thr_arr[t * num_metrics + i]) for i in range(num_metrics)}
                # make a new rwo
                process_data.append(thr_metrics)
            # now merge the data in "row" with the thread 0 data, after removing
            # the threads_df key
            del row['threads_df']
            process_data[0].update(row)
            yield (process_data, row_num, nrows)
            # advance row pointer by 1
            row_num += 1


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
        logger.error("%s", e)
        logger.error("Corrupted CSV or invalid input type")
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
        p.start = earliest_thread_start.to_pydatetime().replace(tzinfo=pytz.utc)
        p.end = latest_thread_finish.to_pydatetime().replace(tzinfo=pytz.utc)
        p.duration = float((latest_thread_finish - earliest_thread_start).total_seconds()) * float(1000000)
    except Exception as e:
        logger.error("%s", e)
        logger.error("missing or invalid value for thread start/end time")
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
    # p.threads_df = df.to_json(orient='split')
    # p.threads_df = {'columns': list(proc[0].keys()), 'data':[]}
    # for thr in proc:
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
    thread_metric_sums = {k: 0 for k in fields}

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


def extract_tags_from_comment_line(jobdatafile, comment="#", tarfile=None):
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
        f = open(jobdatafile, 'r')

    line = f.readline()
    while line:
        line = line.strip()
        if len(line) == 0 or (str(line)).startswith(comment):
            if rows == 0:
                retstr = line[1:].lstrip()
            rows += 1
            line = f.readline()
        else:
            return rows, retstr

    return rows, retstr

#        for member in tar.getmembers():

# def check_experiment_in_metadata(metadata):
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


def _proc_ancestors(pid_map, proc, ancestor_pid, relations=None, descendant_map={}):

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
        if not (relations is None):
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
    sorted_entries = sorted(entries, key=lambda p: p.start)
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
    assert (False)


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
                    for e in entries:
                        assert (e.pid == ppid)
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
def mk_process_tree(j, all_procs=None, pid_map=None):
    if isinstance(j, str):
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
    info_dict.update({'process_tree': 1})
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
def post_process_job(j, all_tags=None, all_procs=None, pid_map=None, update_unprocessed_jobs_table=True, force=False):
    logger = getLogger(__name__)  # you can use other name
    if isinstance(j, str):
        jobid = j
        j = Job[jobid]
    else:
        jobid = j.jobid
    if not force:
        if is_job_post_processed(j):
            logger.warning('skipped processing jobid {0} as it has been already processed'.format(j.jobid))
            return False

    # we need to set up signal handlers so the user doesn't
    # abort the post-processing midway.
    def sig_handler(signo, frame):
        if hasattr(sig_handler, 'interrupted'):
            sys.exit(signo)
        sig_handler.interrupted = True
        print("post-processing job " + jobid + ". Hit Ctrl-C again to safely abort!")

    import atexit
    from epmt.epmtlib import set_signal_handlers
    set_signal_handlers([], sig_handler)

    # restore the signal handler to defaults before we exit
    # set_signal_handlers called without arguments will restore
    # the signal handler to SIG_DFL
    atexit.register(set_signal_handlers)

    logger.info("Starting post-processing of job %s", jobid)
    if not j.info_dict.get('procs_in_process_table', 1):
        stage_copy_result = populate_process_table_from_staging(j)
        if not stage_copy_result:
            logger.error('Aborting post-process of job %s as process copy from staging failed', j.jobid)
            return False
        logger.info('  moving processes from staging complete')
        # we need to expire the job object and make SQLAlchemy reload
        # it as the processes table has changed
        Session.expire(j)
    proc_sums = {}

    _t0 = time.time()
    if not j.processes:
        logger.warning(
            'Job {} contains no processes, perhaps an error in collation or populating the staging data?'.format(jobid))

    if all_tags is None:
        logger.info("  recreating all_tags..")
        all_tags = set()
        # we need to read the tags from the processes
        for p in j.processes:
            if p.tags:
                all_tags.add(dumps(p.tags, sort_keys=True))

    # Add sum of tags to job
    if all_tags:
        logger.info("  found %d distinct sets of process tags", len(all_tags))
        # convert each of the pickled tags back into a dict
        proc_sums['all_proc_tags'] = [loads(t) for t in sorted(all_tags)]
    else:
        logger.debug('  no process tags found in the entire job')
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
    papiex_err_pids = set([])  # set iff rdtsc_duration <= 0
    papiex_err = ''          # set iff rdtsc_duration <= 0
    num_errs = 0             # total error count
    if all_procs:
        logger.info("  computing thread sums across job processes..")
        _t2 = time.time()

        # We no longer do bulk inserts of hosts into the host_associations table
        # Why? The bulk insert doesn't save any time as it bypasses the ORM
        # transaction mechanism. This means we have a race condition, wherein
        # if the transaction is aborted before orm_commit (later in this
        # function), then we have the host_job associations need to be removed
        # So, now we just use the ORM for the host-job associations
        hosts = set()
        for proc in all_procs:
            # see comment above about why we don't use bulk insert for
            # host-job associations
            # if settings.bulk_insert:
            #     hosts.add(proc.host_id)
            # else:
            hosts.add(proc.host)
            nthreads += proc.numtids
            threads_sums_across_procs = sum_dicts(threads_sums_across_procs, proc.threads_sums)

            # non-positive value for rdtsc_duration means either an error
            # in PAPI, a misbehaved process closing a descriptor it doesn't own
            # or, simply an error loading the papiex shared library.
            # We detect the error and keep track of the erroneous processes.
            # Ideally, we would have liked to keep the database IDs of the
            # processes. The problem is that in some cases such as Pony,
            # the database ID of the process is None, until we commit.
            # So, for want of a better option we keep the pids, noting
            # that a PID may be common to more than one process in a job
            rdtsc = proc.threads_sums.get('rdtsc_duration')
            if rdtsc is not None and (rdtsc <= 0):
                num_errs += 1
                # logger.debug('process {} (PID {}) has non-positive rdstc'.format(proc.id, proc.pid))
                papiex_err_pids.add(proc.pid)
                logger.debug('  rdtsc_duration for PID (%d) < 0 (database ID %s)', proc.pid,
                             str(proc.id if proc.id is not None else "not set yet"))
                papiex_err = 'papiex / PAPI library could not be preloaded (rdtsc_duration = 0).' if (
                    rdtsc == 0) else 'PAPI failed or misbehaved process closed a descriptor it did not own (rdtsc_duration < 0).'
                # Set rdtsc_duration to -1 in errant process and threads
                # we need to clone the ORM object as the ORM skips update
                # at times if you just do an in-place field change
                tsums = dict.copy(proc.threads_sums)
                tsums['rdtsc_duration'] = -1
                proc.threads_sums = tsums
                thr_df = proc.threads_df[:]
                for t in thr_df:
                    if t.get('rdtsc_duration', 0) < 0:
                        t['rdtsc_duration'] = -1
                proc.threads_df = thr_df

        logger.info("  job contains %d processes (%d threads)", len(all_procs), nthreads)
        _t3 = time.time()
        logger.debug('  thread sums calculation took: %2.5f sec', _t3 - _t2)
        # see comment above about why we don't use bulk insert for
        # host-job associations
        # if settings.bulk_insert:
        #     logger.debug('  doing a bulk insert of host job associations')
        #     t = Base.metadata.tables['host_job_associations']
        #     thr_data.engine.execute(t.insert(), [ { 'jobid': j.jobid, 'hostname': h } for h in hosts])
        # else:
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

    # If we have a errors, we need to annotate the job
    if num_errs:
        papiex_err += ' {} processes have potentially erroneous PAPI metric counts'.format(num_errs)
        logger.warning('papiex error: %s. Setting rdtsc_duration to -1 for job %s', papiex_err, jobid)
        proc_sums['rdtsc_duration'] = -1  # the current sum is wrong, so use -1
        # use a dict copy so we force an ORM update of this field
        annotations = dict.copy(j.annotations or {})
        annotations['papiex-error'] = papiex_err
        annotations['papiex-error-process-ids'] = sorted(papiex_err_pids)
        j.annotations = annotations

    j.proc_sums = proc_sums

    # the keys below would be missing if the job has no processes
    j.cpu_time = proc_sums.get('usertime', 0) + proc_sums.get('systemtime', 0)

    # we need to create a copy so the ORM actually saves the modifications
    # Merely updating a dict often confuses the ORM and the changes are lost
    info_dict = dict.copy(j.info_dict or {})
    info_dict['post_processed'] = 1
    j.info_dict = info_dict
    _t5 = time.time()
    logger.debug('  proc_sums calculation took: %2.5f sec', _t5 - _t4)
    logger.info('  job %s has been post-processed', jobid)

    if not settings.lazy_compute_process_tree:
        mk_process_tree(j, all_procs)

    # The calculation below has been moved to before post-processing
    #
    # the cpu time for a job is the sum of the exclusive times
    # of all processes in the job
    # We use list-comprehension and aggregation over slower ORM ops
    # j.cpu_time = orm_sum_attribute(j.processes, 'cpu_time')
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
                logger.info('  marking job %s as processed in database', jobid)
                orm_commit()
            logger.debug(
                '  checking/updating unprocessed jobs table (includes implicit commit) took: %2.5f sec',
                time.time() - _t6)
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

def populate_process_table_from_staging(j):
    '''
    Populate the processes table by moving the process rows
    from the processes_staging table and doing necessary
    field manipulations.

    Parameters
    ----------
          j: ORM job object

    Returns
    -------
    True on sucess, and False on error

    Notes
    -----
    The database operations are done in a transaction so
    they should be no partial state change. On success,
    the rows from the staging table will be removed, and
    have been added to the processes table. Unfortunately,
    we cannot use a native database row copy, because the
    field formats change and we need to do some field manipulations.
    In particular, thread metric sums are computed, and a flattened
    1-D threads_df is convered to a JSON.

    It is implicitly assumed that we are connecting to a Postgresql
    database (since SQLite doesn't support direct CSV copy in the
    first place).
    '''
    import datetime as dt
    import psycopg2
    logger = getLogger(__name__)  # you can use other name
    jobid = j.jobid
    job_info_dict = j.info_dict
    logger.info('  moving job {} processes from staging -> process table..'.format(jobid))
    metric_names = j.info_dict['metric_names'].split(',')
    # get the row IDs of the starting and ending row for the job
    # in the staging table
    (first_proc_id, last_proc_id) = j.info_dict['procs_staging_ids']
    num_procs = last_proc_id - first_proc_id + 1

    # we process around 3K procs/sec, so if this operation will
    # take longer than 5sec, let's warn the user
    if num_procs > 15000:
        logger.warning('Moving staged processes for job ' + jobid + ' will take approx. %2.0f sec..', num_procs / 3000)

    staged_procs = orm_raw_sql(
        "SELECT id, threads_df, start, finish, tags, hostname, numtids, exename, path, args, pid, ppid, pgid, sid, generation, exitcode, exitsignal FROM processes_staging WHERE id BETWEEN {} AND {}".format(
            first_proc_id,
            last_proc_id))
    proc_ids = []
    nprocs = 0
    insert_sql = ""
    _start_time = time.time()
    # notice the quoted "end" field. end is a reserved word in SQL
    prefix_insert_sql = "INSERT INTO processes(jobid,duration,tags,host_id,threads_df,threads_sums,numtids,cpu_time,exename,path,args,pid,ppid,pgid,sid,gen,exitcode,start,\"end\") VALUES "
    for proc_row in staged_procs:
        nprocs += 1
        (proc_id, threads_df, start, finish, tags, host_id, numtids, exename,
         path, args, pid, ppid, pgid, sid, gen, exitcode, exitsignal) = proc_row
        proc_ids.append(proc_id)
        duration = finish - start  # in us
        # convert from unix timestamp to python datetime
        start = dt.datetime.fromtimestamp(start / 1e6)
        end = dt.datetime.fromtimestamp(finish / 1e6)

        # take care to escape characters using psycopg2's adapat
        tags = psycopg2.extensions.adapt(dumps(tag_from_string(tags) if tags else {}))
        if args is None:
            args = ''
        args = args.replace('%', '%%')
        args = psycopg2.extensions.adapt(args)

        threads_sums = {metric_names[i]: int(threads_df[i]) for i in range(len(metric_names))}
        for t in range(1, numtids):
            for i in range(len(metric_names)):
                # threads_df is a flattened list where each thread's metrics are
                # adjacent to the previous
                threads_sums[metric_names[i]] += int(threads_df[t * len(metric_names) + i])
        cpu_time = threads_sums.get('usertime', 0) + threads_sums.get('systemtime', 0)
        # threads_sums is to be saved as JSON
        threads_sums = dumps(threads_sums)

        # threads_df is a flattened list where each thread's metrics are
        # are placed next the previous one. Here we make it into a
        # list of dicts
        _thr_dict_list = []
        for t in range(numtids):
            _thr_dict_list.append({metric_names[i]: int(threads_df[t * len(metric_names) + i])
                                  for i in range(len(metric_names))})
        # threads_df is to be saved as JSON
        threads_df = dumps(_thr_dict_list)

        insert_sql += prefix_insert_sql + """('{jobid}',{duration},{tags},'{host_id}','{threads_df}','{threads_sums}',{numtids},{cpu_time},'{exename}','{path}',{args},{pid},{ppid},{pgid},{sid},{gen},{exitcode},'{start}','{end}');\n""".format(
            jobid=jobid,
            start=start,
            end=end,
            duration=duration,
            tags=tags,
            host_id=host_id,
            threads_df=threads_df,
            threads_sums=threads_sums,
            numtids=numtids,
            cpu_time=cpu_time,
            exename=exename,
            path=path,
            args=args,
            pid=pid,
            ppid=ppid,
            pgid=pgid,
            sid=sid,
            gen=gen,
            exitcode=exitcode)

    # sql to delete the rows from the staging table
    delete_sql = "DELETE FROM processes_staging WHERE id BETWEEN {} AND {};\n".format(first_proc_id, last_proc_id)

    job_info_dict['procs_in_process_table'] = 1

    # these fields are meaningless after procs have been moved to the processes table
    # so we remove them from the job info_dict
    del job_info_dict['procs_staging_ids']

    # We want to retain the metric_names in the job info_dict, so don't remove
    # it below, anymore
    # del job_info_dict['metric_names']

    update_job_sql = "UPDATE jobs SET info_dict = '{}' WHERE jobid = '{}'".format(dumps(job_info_dict), jobid)

    # now do a transaction
    try:
        # orm_raw_sql(insert_sql+delete_sql+update_job_sql, commit=True)
        logger.debug('executing: orm_raw_sql(insert_sql,commit=True)')
        orm_raw_sql(insert_sql, commit=True)
        logger.debug('executing: orm_raw_sql(delete_sql,commit=True)')
        orm_raw_sql(delete_sql, commit=True)
        logger.debug('executing: orm_raw_sql(update_job_sql,commit=True)')
        orm_raw_sql(update_job_sql, commit=True)
    except Exception as e:
        err_str = str(e)
        msg = 'Error copying from staging to process table for job ' + jobid
        logger.error(msg)
        if 'permission denied' in err_str:
            logger.error('You do not have sufficient privileges for this operation')
        else:

            logger.error(
                f'related to error? .... insert_sql[:{settings.max_log_statement_length}] = {insert_sql[:settings.max_log_statement_length]}')
            logger.error(f'related to error? .... delete_sql = {delete_sql}')
            logger.error(f'related to error? .... update_job_sql = {update_job_sql}')

            # Only log the first 100 or so of errors
            if len(err_str) > settings.max_log_statement_length:
                logger.error(f'error (type is {type(err_str)}) too long to show ({len(err_str)})... ')
                logger.error(f'first {settings.max_log_statement_length} errors in err_str list are...')
                logger.error(''.join(err_str[:settings.max_log_statement_length]))
            else:
                logger.error(err_str)
        return False
    table_copy_time = time.time() - _start_time
    logger.warning("  copied %d processes from staging in %2.5f sec at %2.5f procs/sec",
                   nprocs, table_copy_time, nprocs / table_copy_time)
    return True


@db_session
def ETL_job_dict(raw_metadata, filedict, settings, tarfile=None):
    logger = getLogger(__name__)  # you can use other name
    job_init_start_time = time.time()
    # Synthesize what we need
    # it's safe and fast to call the check_fix_metadata
    # it will not waste time re-checking (since it marks the metadata as checked)
    metadata = check_fix_metadata(raw_metadata)
    if metadata is False:
        return (False, 'Error: Could not get valid metadata', ())
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
        tz_str = get_first_key_match(
            env_dict, 'TZ', 'TIMEZONE') or get_first_key_match(
            environ, 'EPMT_TZ') or 'US/Eastern'
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
    annotations = metadata.get('annotations', {})
    if annotations:
        logger.info('Job annotations: {0}'.format(annotations))
        if settings.job_tags_env in annotations:
            job_tag_from_ann = tag_from_string(annotations[settings.job_tags_env])
            if job_tags and job_tag_from_ann:
                if (job_tags != job_tag_from_ann):
                    err_msg = 'Metadata and annotations contain different job tags:\n{} (metadata),\n{} (annotations)'.format(
                        job_tags, job_tag_from_ann)
                    return (False, err_msg, ())
                else:
                    logger.warning('Both metadata and annotations have the same job tags')
            job_tags = job_tag_from_ann or job_tags
    if job_tags and not (settings.job_tags_env in annotations):
        # set annotation based on metadata job tags (if it is not set)
        from epmt.epmtlib import tag_dict_to_string
        tag_str = tag_dict_to_string(job_tags)
        logger.debug(
            'updating {} in annotations to {} based on metadata job tags'.format(
                settings.job_tags_env, tag_str))
        annotations[settings.job_tags_env] = tag_str

    # sometimes script name is to be found in the job tags
    if (job_status.get('script_name') is None) and job_tags and job_tags.get('script_name'):
        job_status['script_name'] = job_tags.get('script_name')

    # info_dict = metadata['job_pl_from_batch'] # end batch also

    logger.info("Processing job id %s", jobid)

    # Initialize elements used in compute
    then = datetime.now()
    csvt = timedelta()
    earliest_process = datetime.utcnow().replace(tzinfo=pytz.utc)
    latest_process = datetime.fromtimestamp(0).replace(tzinfo=pytz.utc)

    # stdout.write('-')
    ## Hostname, job, metricname objects
    ## Iterate over hosts

    logger.debug("Iterating over %d hosts for job ID %s, user %s...", len(filedict.keys()), jobid, username)

    #
    # Create user and job object
    #
    from sqlalchemy import exc
    try:
        u = lookup_or_create_user(username)
    except exc.IntegrityError as e:
        # The insert failed due to a concurrent transaction
        Session.rollback()
        # the user must exist now
        u = lookup_or_create_user(username)

    j = create_job(jobid, u)
    if j is None:
        return (False, 'Assuming job {} is already in database'.format(str(jobid)), ())

    j.jobname = jobname
    j.exitcode = exitcode
    j.annotations = annotations
# fix below
    j.env_dict = env_dict
    j.env_changes_dict = env_changes_dict
    if job_tags:
        logger.info('Job tags: {}'.format(job_tags))
    j.tags = job_tags if job_tags else {}
    job_init_fini_time = time.time()
    logger.debug('job init took: %2.5f sec', job_init_fini_time - job_init_start_time)
    # save naive datetime objects in the database
    j.start = start_ts.replace(tzinfo=None)
    j.end = stop_ts.replace(tzinfo=None)
    j.submit = submit_ts.replace(tzinfo=None)  # Wait time is start - submit and should probably be stored
    info_dict = {
        'tz': start_ts.tzinfo.tzname(None),
        'status': job_status,
        'procs_in_process_table': 0,
        'post_processed': 0}
    j.duration = int((j.end - j.start).total_seconds() * 1000000)
    logger.info("Computed duration of job %s: %f us, %.2f m", jobid, j.duration, j.duration / 60000000)

    didsomething = False
    all_tags = set()
    all_procs = []
    total_procs = 0
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

    copy_csv_direct = False
    for hostname, files in filedict.items():
        if hostname == "unknown":
            logger.warning('could not determine hostname from filedict, picking it from metadata instead')
            hostname = metadata.get('job_pl_hostname', '')
            if not hostname:
                logger.warning('could not determine hostname from metadata either')
        logger.debug("Processing host %s", hostname)
        h = None
        if hostname:
            h = lookup_or_create_host_safe(hostname)
        cntmax = len(files)
        cnt = 0
        nrecs = 0
        fileno = 0
        csv = datetime.now()
        fmt = '1'  # default csv format
        header_filename = "{}-papiex-header.tsv".format(hostname)
        if tarfile:
            logger.debug('checking if tarfile contains CSV v2 files')
            try:
                csv_hdr_info = tarfile.getmember('./' + header_filename)
                csv_hdr_flo = tarfile.extractfile(csv_hdr_info)
                fmt = '2'
            except KeyError:
                # that means the header does not exist and we have CSV v1 format
                pass
            except Exception as e:
                msg = "could not extract CSV v2 header file: ", str(e)
                logger.error(msg)
                return (False, msg, ())
        else:
            # we are ingesting from a directory. Check if file has a .tsv suffix
            if files[0].endswith('.tsv'):
                fmt = '2'
                # get the directory containing the .tsv so we can
                # open the papiex header in the same file
                submit_dir = dirname(files[0])
                full_hdr_path = submit_dir + '/' + header_filename
                try:
                    csv_hdr_flo = open(full_hdr_path, 'r')
                except Exception as e:
                    msg = 'Could not open {} for reading: {}'.format(full_hdr_path, str(e))
                    logger.error(msg)
                    return (False, msg, ())

        logger.info('CSV v{} files detected in tar: {}'.format(fmt, ",".join(files)))

        # get the metric names from the CSV header file if we have csv v2
        # for v1 they will be determined automatically from the headers in
        # the collated file
        # metric_names is a comma-separated string
        metric_names = ''
        if fmt == '2':
            from epmt.epmt_convert_csv import OUTPUT_CSV_FIELDS, OUTPUT_CSV_SEP
            # read the header file and get metric names
            csv_headers = csv_hdr_flo.read()
            csv_hdr_flo.close()
            # csv headers might be a regular string or a byte stream
            # if it's the latter, then use map to convert it to a list
            # of strings, join and then split to get an array of headers.
            # If it's already a string, then just split to get the header array
            if isinstance(csv_headers, str):
                csv_headers = csv_headers.split(OUTPUT_CSV_SEP)
            else:
                csv_headers = "".join(map(chr, csv_headers)).split(OUTPUT_CSV_SEP)
            # remove leading/trailing whitespace in column names
            csv_headers = [h.strip() for h in csv_headers]
            logger.debug('papiex headers: {}'.format(csv_headers))
            metric_names = csv_headers[OUTPUT_CSV_FIELDS.index('threads_df')]
            metric_names = metric_names.replace('{', '').replace('}', '')
            logger.debug('per-thread metric names: {}'.format(metric_names))
            # save the metric_names in job info_dict for future use (such as when creating
            # threads_df from a flattened array
            info_dict['metric_names'] = metric_names

        for f in files:
            fileno += 1
            _file_io_start_ts = time.time()
            logger.debug("Processing file %s (%d of %d)", f, fileno, cntmax)
#
#            stdout.write('\b')            # erase the last written char
#            stdout.write(spinner.next())  # write the next character
#            stdout.flush()                # flush stdout buffer (actual character display)
#
# We need rows to skip
# oldproctag (after comment char) is outdated as a process tag but kept for posterities sake
            skiprows, oldproctag = extract_tags_from_comment_line(f, tarfile=tarfile)
            logger.debug("%s had %d comment rows, oldproctags %s", f, skiprows, oldproctag)
            if tarfile:
                logger.debug('extracting {} from tar'.format(f))
                info = tarfile.getmember(f)
                flo = tarfile.extractfile(info)
            else:
                flo = open(f, 'rb')
            if (fmt == '2' and (orm_db_provider() == 'postgres') and (settings.orm == 'sqlalchemy')):
                import psycopg2
                logger.info('Doing a fast ingest of {}'.format(flo.name))
                _conn_start_ts = time.time()
                try:
                    conn = psycopg2.connect(settings.db_params['url'])
                except Exception as e:
                    msg = 'Error establishing connection to PostgreSQL database: {}'.format(str(e))
                    logger.error(msg)
                    return (False, msg, ())

                cur = conn.cursor()
                _copy_start_ts = time.time()
                logger.debug('establishing connection to DB took: %2.5f sec', _copy_start_ts - _conn_start_ts)
                copy_sql = "COPY processes_staging({}) FROM STDIN DELIMITER '{}' CSV QUOTE E'\b'".format(
                    ",".join(OUTPUT_CSV_FIELDS), OUTPUT_CSV_SEP)
                logger.debug('Issuing direct-copy SQL: ' + copy_sql)
                try:
                    # copy_from is deprecated and copy_expert is recommended
                    # Also, copy_from cannot handle a HEADER option
                    # cur.copy_from(flo, 'processes_staging', sep=OUTPUT_CSV_SEP, columns=OUTPUT_CSV_FIELDS)
                    cur.copy_expert(copy_sql, flo)
                    # the rowcount represents the number of rows copied
                    num_procs_copied = cur.rowcount
                    # we need to determine the last row id, so we
                    # know the job spans from which row to which row.
                    # We will save this information in the job metadata in the
                    # database, so we know which rows to move from staging
                    # to the process table when processing the job
                    cur.execute('SELECT LASTVAL()')
                    lastid = cur.fetchone()[0]
                    conn.commit()
                except Exception as e:
                    msg = 'copy_expert to processes_staging {}'.format(str(e))
                    logger.error(msg)
                    conn.rollback()
                    continue

                if conn:
                    conn.close()
                copy_processes_time = time.time() - _copy_start_ts
                flo.close()
                logger.info('direct CSV copy of %d processes took: %2.5f sec, at %2.5f procs/sec',
                            num_procs_copied, copy_processes_time, num_procs_copied / copy_processes_time)
                didsomething = (num_procs_copied > 0)
                copy_csv_direct = True
                total_procs += num_procs_copied
                # save the staging table row id range for the job
                info_dict['procs_staging_ids'] = (lastid - num_procs_copied + 1, lastid)
                logger.debug('job process_staging ID range: {}'.format(
                    lastid if num_procs_copied == 1 else info_dict['procs_staging_ids']))
                continue

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
            for (proc, _, nrows) in get_proc_rows(csv_file, skiprows, fmt, metric_names.split(',')):
                _load_process_from_df_start_ts = time.time()
                p = load_process_from_dictlist(proc, h, j, u, settings, profile)
                load_process_from_df_time += time.time() - _load_process_from_df_start_ts
                if not p:
                    logger.error("Failed loading process, file %s!", f)
                    continue

                if 'metric_names' not in info_dict:
                    # save the metric names in the info_dict
                    # only need to do this once
                    info_dict['metric_names'] = ",".join(sorted(p.threads_sums.keys()))

                # If using old version of papiex, process tags are in the comment field
                _proc_tag_start_ts = time.time()
                if not p.tags:
                    p.tags = tag_from_string(oldproctag) if oldproctag else {}
                # pickle and add tag dictionaries to a set
                # remember to sort_keys during the pickle!
                if p.tags:
                    all_tags.add(dumps(p.tags, sort_keys=True))
                proc_tag_process_time += time.time() - _proc_tag_start_ts
                _t = time.time()
                
                # We shouldn't be seeing a pid repeat in a job.
                # Theoretically it's posssible but it would complicate the pid map a bit
                # assert(p.pid not in pid_map)
                pid_map[p.pid] = p
                all_procs.append(p)
                total_procs += 1
                
                # Compute duration of job
                if (p.start < earliest_process):
                    earliest_process = p.start
                    root_proc = p
                #if (p.end > latest_process):
                #    latest_process = p.end
                latest_process = max(latest_process, p.end)

                # correct the process start/stop times for timezone
                # start_ts and end_ts are timezone-aware datetime objects
                p.start = p.start.replace(tzinfo=pytz.utc).astimezone(tz=tz_default)
                p.end = p.end.replace(tzinfo=pytz.utc).astimezone(tz=tz_default)
                if ((p.start < start_ts) or (p.end > stop_ts)):
                    msg = 'Corrupted CSV detected: Process ({0}, pid {1}) start/finish times ({2}, {3}) do not fall within job interval ({4}, {5}). Bailing on job ingest..'.format(
                        p.exename, p.pid, p.start, p.end, start_ts, stop_ts)
                    logger.error(msg)
                    raise ValueError(msg)
                
                # save naive datetime objects in the database
                p.start = p.start.replace(tzinfo=None)
                p.end = p.end.replace(tzinfo=None)

                # Debugging/    progress
                cnt += 1
                nrecs += p.numtids
                csvt = datetime.now() - csv
                if (((nrecs % 1000) == 0) or
                    ((cntmax == 1) and (nrecs == nrows)) or
                        ((cntmax > 1) and (fileno == cntmax))):
                    if cntmax > 1:
                        # many small files each with a single process
                        logger.info("Did %d (%d/%d files)...%.2f/sec", nrecs,
                                    fileno, cntmax, nrecs / csvt.total_seconds())
                    else:
                        # collated file
                        logger.info("Did %d (%d in file)...%.2f/sec", nrecs, nrows, nrecs / csvt.total_seconds())
                    # break
                proc_misc_time += time.time() - _t

            df_process_time += time.time() - _df_process_start_ts

        if cnt:
            didsomething = True

    # these stats and the processing below are meaningful for
    # the case when the data has not been directly ingested into the db
    if not copy_csv_direct:
        logger.debug('file I/O time took: %2.5f sec', file_io_time)
        logger.debug('process load ops took: %2.5f sec', df_process_time)
        logger.debug('  - load process from dictlist took: %2.5f sec', load_process_from_df_time)
        logger.debug('    - {0}'.format(["%s: %2.5f sec" % (k, v) for (k, v) in profile.load_process.items()]))
        logger.debug('  - tag processing took: %2.5f sec', proc_tag_process_time)
        logger.debug('  - proc misc. processing took: %2.5f sec', proc_misc_time)
        logger.debug(
            '  - get_proc_rows took: %2.5f sec',
            df_process_time -
            load_process_from_df_time -
            proc_tag_process_time -
            proc_misc_time)

        if filedict:
            if not didsomething:
                logger.warning("Something went wrong in parsing process data files")
                return (False, "Error parsing CSV", ())
        else:
            logger.warning("job %s, user %s, jobname %s has no process data", jobid, username, jobname)

        # procs are not in staging table they will be in the processes table
        info_dict['procs_in_process_table'] = 1

        # cpu_time is now computed during post-process to unify code paths
        # j.cpu_time = reduce(lambda c, p: c + p.cpu_time, all_procs, 0)
        # j.cpu_time = sum([p.cpu_time for p in all_procs])

        # logger.info("Earliest process start: %s",j.start)
        # logger.info("Latest process end: %s",j.end)

        if root_proc:
            # if root_proc.exitcode != j.exitcode:
            #     logger.warning('metadata shows the job exit code is {0}, but root process exit code is {1}'.format(j.exitcode, root_proc.exitcode))
            j.exitcode = root_proc.exitcode
            logger.info('job exit code (using exit code of root process): {0}'.format(j.exitcode))
        if j.exitcode != 0:
            logger.warning('Job failed with a non-zero exit code({})'.format(j.exitcode))

        if settings.bulk_insert and all_procs:
            logger.info('doing a bulk insert of {0} processes'.format(len(all_procs)))
            _b0 = time.time()
            # thr_data.engine.execute(Process.__table__.insert(), all_procs)
            Session.bulk_insert_mappings(Process, all_procs)
            logger.info('bulk insert of processes took: %2.5f sec', time.time() - _b0)

    j.info_dict = info_dict

    if settings.post_process_job_on_ingest and not copy_csv_direct:
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
        # mark job as unprocessed. It will need post-processing later
        try:
            logger.debug('inserting **UNPROCESSED** reference for job %s', j.jobid)
            orm_create(UnprocessedJob, jobid=j.jobid)
        except exc.IntegrityError as e:
            logger.warning('**UNPROCESSED** reference for job %s already exists', j.jobid)
            Session.rollback()
            return (False, "Job already in database (unprocessed)", ())

    logger.debug("Committing job %s to database", j.jobid)
    _c0 = time.time()
    orm_commit()
    logger.debug("Commit time: %2.5f sec", time.time() - _c0)
    now = datetime.now()
    logger.info("Staged import of job %s with %d processes took %s, %f processes/sec",
                j.jobid, total_procs, now - then, total_procs / float((now - then).total_seconds()))
    print("Imported successfully - job:", jobid, "processes:", total_procs,
          "rate:", total_procs / float((now - then).total_seconds()))
    return (True, 'Import successful', (j.jobid, total_procs))


def post_process_pending_jobs():
    '''
       This function will post-process all pending jobs that have
       not been post-processed.
       It returns the list of jobids that were post-processed.
    '''
    # we only support post-processing for SQLA at the moment
    if settings.orm != 'sqlalchemy':
        logger.error("post-processing is not supported for Pony")
        return []

    unproc_jobs = orm_findall(UnprocessedJob)
    did_process = []
    for u in unproc_jobs:
        jobid = u.jobid
        j = u.job
        logger.debug('post-processing {0}'.format(jobid))
        if post_process_job(jobid):
            did_process.append(jobid)
    return did_process
