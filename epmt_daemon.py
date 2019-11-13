from __future__ import print_function
from logging import getLogger
from getpass import getuser

logger = getLogger(__name__)  # you can use other name

PID_FILE = '/tmp/epmt.pid.' + getuser()

def start_daemon(lockfile = PID_FILE):
    from os import path
    if (path.exists(lockfile)):
        logger.warning('Lock file exists. Perhaps a daemon is already running. If not, please remove the lock file ({0}) and try again'.format(lockfile))
        return(-1)
    from daemon import DaemonContext, pidfile
    # start daemon
    logger.info('Starting EPMT daemon (lockfile: {0})..'.format(lockfile))
    with DaemonContext(pidfile=pidfile.PIDLockFile(lockfile)):
        daemon_loop()
    return 0

def _get_daemon_pid(pidfile = PID_FILE):
    try:
        with open(pidfile, 'r') as f:
            pid = f.read().strip()
        logger.debug('Found daemon lockfile with PID({0})'.format(pid))
    except IOError:
        return -1
    except Exception as e:
        logger.warning(str(e))
        return -2
    return (int(pid))

def is_daemon_running(pidfile = PID_FILE):
    pid = _get_daemon_pid(pidfile)
    if pid < 0:
        return False
    from epmtlib import check_pid
    return check_pid(pid)[0]
    


def stop_daemon(pidfile = PID_FILE):
    pid = _get_daemon_pid(pidfile)
    if pid < 0:
        logger.warning('No lock file found. Is the daemon even running?')
        return pid
    from epmtlib import check_pid
    if check_pid(pid)[0]:
        from os import kill
        from signal import SIGINT
        logger.warning('Sending SIGINT to EPMT daemon with PID({0})'.format(pid))
        try:
            kill(pid, SIGINT)
        except Exception as e:
            logger.warning('Error killing process (PID {0}): {1}'.format(pid, str(e)))
            return -1
    else:
        logger.warning('No such process exists. Perhaps the daemon died?')
        return pid

    # normally the lock file is removed already. Just in case it isn't
    # perhaps because the process had been killed with SIGKILL, we will
    # remove the stale lock file. Make sure to ignore any exceptions, 
    # since you can count on getting an IOError for file not found
    from os import unlink
    try:
        unlink(pidfile)
    except:
        pass
    return 0

def print_daemon_status(pidfile = PID_FILE):
    pid = _get_daemon_pid(pidfile)
    if pid < 0:
        print('EPMT daemon is not running.')
        return 0
    else:
        logger.debug('Found lock file (PID: {0})'.format(pid))
    from epmtlib import check_pid
    rc = check_pid(pid)
    print('EPMT daemon running OK (pid: {0})'.format(pid) if rc[0] else 'EPMT daemon is not running. You should probably remove the stale lock file ({0}).'.format(pidfile))
    return 0

def daemon_loop():
    from time import sleep, time
    from epmt_query import get_unprocessed_jobs, get_unanalyzed_jobs, comparable_job_partitions, analyze_jobs
    from epmt_job import post_process_outstanding_jobs
    while True:
        delay = 10 # in seconds
        _t1 = time()
        # unprocessed jobs (these are jobs on whom post-processing
        # pipeline hasn't run; these are different from jobs on whom
        # the analysis pipeline hasn't run)
        # The post-processing pipeline computes the process tree
        post_process_outstanding_jobs()
        ua_jobs = get_unanalyzed_jobs()
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
                analyze_jobs(jobids, check_comparable = False)
        _loop_time = (time() - _t1)
        delay = delay - _loop_time
        if delay > 0:
            logger.debug('sleeping for {0} sec'.format(delay))
            sleep(delay)
        else:
            logger.warning("daemon loop took {0} seconds. No sleep for me!".format(_loop_time))
