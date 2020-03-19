from __future__ import print_function
from logging import getLogger
from getpass import getuser
from os import getpid


logger = getLogger(__name__)  # you can use other name

# PID_FILE = '/tmp/epmt.{}.{}'.format(getpid(), getuser())
PID_FILE = '/tmp/epmt.pid.' + getuser()

# we use this global so we can force exit if
# more than one signal is received. Otherwise,
# in each iteration of the daemon we will check if
# we received a signal earlier and stop gracefully.
# A global is unfortunately necessary as this variable
# is shared between the signal handler and the daemon loop
sig_count = 0



def start_daemon(lockfile = PID_FILE):
    import logging
    logger = getLogger(__name__)  # you can use other name
    from os import path
    if (path.exists(lockfile)):
        logger.warning('Lock file exists. Perhaps a daemon is already running. If not, please remove the lock file ({0}) and try again'.format(lockfile))
        return(-1)

    # set up signal handlers
    # from signal import SIGHUP, SIGTERM, SIGQUIT, SIGINT, SIGUSR1, signal
    # for sig in [SIGHUP, SIGTERM, SIGQUIT, SIGINT, SIGUSR1]:
    #     signal(sig, signal_handler)
    # logger.debug('Finished setting up signal handlers')

    from daemon import DaemonContext, pidfile
    context = DaemonContext()
    context.pidfile =  pidfile.PIDLockFile(lockfile)
    context.signal_map = {}
    # daemon_args = { 'pidfile': pidfile.PIDLockFile(lockfile), 'signal_map': {} }
    # set up signal handlers
    from signal import SIGHUP, SIGTERM, SIGQUIT, SIGINT, SIGUSR1
    for sig in [SIGHUP, SIGTERM, SIGQUIT, SIGINT, SIGUSR1]:
        context.signal_map[sig] = signal_handler

    # ensure logging uses the same file-descriptors and they are preserved
    # across the fork
    logger_files = []
    try:
        for handler in logging.root.handlers:
            fileno = handler.stream.fileno()
            logger_files.append(fileno)
        if logger_files:
            # daemon_args['files_preserve'] = logger_files
            context.files_preserve = logger_files
    except:
        logger.warning('could not get file descriptor for logging in daemon')

    # start daemon
    logger.info('Starting the EPMT daemon (lock file: {0})..'.format(lockfile))
    print('Starting the EPMT daemon..')
    with context:
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
        from signal import SIGUSR1
        logger.warning('Sending signal to EPMT daemon with PID({0})'.format(pid))
        try:
            kill(pid, SIGUSR1)
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
        print('EPMT daemon is not running. Start it with "epmt daemon --start"')
        return 0
    from epmtlib import check_pid
    rc = check_pid(pid)
    print('EPMT daemon running OK (pid: {0}). Stop it with "epmt daemon --stop"'.format(pid) if rc[0] else 'EPMT daemon is not running. You should probably remove the stale lock file ({0}).'.format(pidfile))
    return 0

# if niters is set, then the daemon loop will end after 'niters' iterations
# otherwise loop forever or until we get interrupted by a signal
def daemon_loop(niters = 0):
    global sig_count
    sig_count = 0
    logger = getLogger(__name__)  # you can use other name
    from time import sleep, time
    from epmt_query import analyze_pending_jobs
    from epmt_job import post_process_pending_jobs
    logger.debug('starting daemon loop..')
    tot_pp_runs = 0
    tot_ua_runs = 0
    iters = 0
    while (True):
        if (sig_count > 0):
            logger.warning('Terminating EPMT daemon gracefully..')
            from sys import exit
            exit(0)
        delay = 10 # in seconds
        _t1 = time()
        # unprocessed jobs (these are jobs on whom post-processing
        # pipeline hasn't run; these are different from jobs on whom
        # the analysis pipeline hasn't run)
        # The post-processing pipeline computes the process tree
        num_pp_run = len(post_process_pending_jobs())
        tot_pp_runs += num_pp_run
        # now run the analyses pipelines (outlier detection, etc)
        num_analyses_run = analyze_pending_jobs()
        tot_ua_runs += num_analyses_run
        logger.debug('{0} jobs post-processed; {1} analyses filters run'.format(num_pp_run, num_analyses_run))
        iters += 1
        if niters and (iters > niters):
            logger.debug('ending daemon loop, as requested iterations completed')
            break
        _loop_time = (time() - _t1)
        delay = delay - _loop_time
        if delay > 0:
            logger.debug('sleeping for {0} sec'.format(delay))
            sleep(delay)
        else:
            logger.warning("daemon loop took {0} seconds. No sleep for me!".format(_loop_time))
    return (tot_pp_runs, tot_ua_runs)

def signal_handler(signum, frame):
    global sig_count
    if sig_count > 0:
        # logger.warning('Received multiple signals to terminate. Terminating now!')
        from sys import exit
        exit(signum)
    else:
        # let the daemon loop know that we should exit gracefully at the
        # very next opportunity
        # logger.warning('Received signal; will terminate shortly..')
        sig_count = 1
    return None
