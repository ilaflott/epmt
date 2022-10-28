from __future__ import print_function
import logging
from getpass import getuser
from os import path
from os import kill
from os import unlink
from os import getppid
from sys import exit
from time import sleep, time
from daemon import DaemonContext, pidfile
from signal import SIGHUP, SIGTERM, SIGQUIT, SIGINT, SIGUSR1
from epmtlib import find_files_in_dir
from epmt_cmds import epmt_submit
from epmt_query import analyze_jobs, get_unprocessed_jobs, post_process_jobs
from epmtlib import check_pid, epmt_logging_init
from epmt_cmd_retire import epmt_retire
import epmt_settings as settings
from orm import orm_db_provider
    
logger = logging.getLogger(__name__)  # you can use other name

PID_FILE = '/tmp/epmt.pid.' + getuser()

# we use this global so we can force exit if
# more than one signal is received. Otherwise,
# in each iteration of the daemon we will check if
# we received a signal earlier and stop gracefully.
# A global is unfortunately necessary as this variable
# is shared between the signal handler and the daemon loop
sig_count = 0

def start_daemon(foreground = False, lockfile = PID_FILE, **daemon_args):
    stat, pid = is_daemon_running(lockfile)
    if stat:
        logger.error('Daemon may be still running at pid {0}. If not, please remove the lock file {1} and try again'.format(pid,lockfile))
        return(-1)
    # set up signal handlers
    # from signal import SIGHUP, SIGTERM, SIGQUIT, SIGINT, SIGUSR1, signal
    # for sig in [SIGHUP, SIGTERM, SIGQUIT, SIGINT, SIGUSR1]:
    #     signal(sig, signal_handler)
    # logger.debug('Finished setting up signal handlers')

    if foreground:
        from contextlib import nullcontext
        context = nullcontext()
    else:
        context = DaemonContext()
        context.pidfile =  pidfile.PIDLockFile(lockfile)
        context.signal_map = {}
        # daemon_args = { 'pidfile': pidfile.PIDLockFile(lockfile), 'signal_map': {} }
        # set up signal handlers
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
    logger.info('Using lock file {0} for the EPMT daemon'.format(lockfile))
    exit(daemon_loop(context,**daemon_args))
    return 0

def is_daemon_running(pidfile = PID_FILE):
    logger.debug("Looking for file %s to fetch daemon pid",pidfile)
    try:
        with open(pidfile, 'r') as f:
            pid = f.read().strip()
        logger.debug('Found daemon lockfile with PID({0})'.format(pid))
#    except IOError:
#        return -1
    except Exception as e:
        logger.debug(str(e))
        return False, -1
    if int(pid) < 0:
        logger.error('PID %d for daemon is less than 0, this cant be true',int(pid))
        return False, -1
    stat, msg = check_pid(int(pid))
    if not stat:
#        logger.warning("PID %d for daemon doesn't seem alive: %s",int(pid),msg)
        logger.error("You should check PID {0} and consider removing the stale lock file {1}.".format(int(pid),pidfile))
        return False, -1
    return True, int(pid)

def stop_daemon(pidfile = PID_FILE):
    stat, pid = is_daemon_running(pidfile)
    if stat:
        logger.info('Sending SIGUSR1 signal to EPMT daemon PID {0}'.format(pid))
        try:
            print("Sending SIGUSR1 to EPMT daemon pid "+str(pid))
            kill(pid, SIGUSR1)
        except Exception as e:
            logger.error('Error killing process PID {0}: {1}'.format(pid, str(e)))
            return -1
    else:
        logger.error('EPMT daemon not running, start with "epmt daemon --start"')
        return -1

    # normally the lock file is removed already. Just in case it isn't
    # perhaps because the process had been killed with SIGKILL, we will
    # remove the stale lock file. Make sure to ignore any exceptions, 
    # since you can count on getting an IOError for file not found
    try:
        unlink(pidfile)
    except:
        pass
    return 0

def print_daemon_status(pidfile = PID_FILE):
    stat, pid = is_daemon_running(pidfile)
    if not stat:
        logger.error('EPMT daemon not running, start with "epmt daemon --start"')
        return -1
    else:
    	print('EPMT daemon running PID {0}. stop with "epmt daemon --stop"'.format(pid))
    return 0

# if niters is set, then the daemon loop will end after 'niters' iterations
# otherwise loop forever or until we get interrupted by a signal
def daemon_loop(context, niters = 0, post_process = True, analyze = True, retire = False, ingest = False, recursive = False, keep = False, verbose = 0):
    '''
    Runs a daemon loop niters times, performing enabled actions
    such as post-processing, ingestion, etc.

          niters: Number of times to run the daemon loop
    post_process: Perform post-process of unprocessed
                  jobs. Default True.
         analyze: Perform analysis on post-processed jobs. Default True.
          retire: Perform data retirement based on data retention policy
          ingest: Perform ingestion from the "ingest" directory into
                  the database. Default is disabled.
       recursive: Only meaningful when ingest is set. It indicates whether
                  EPMT should descend into subdirectories to find staged files
                  or not. Default False.
            keep: Only meaningful when ingest is set. It indicates whether
                  on successful ingest the file should be retained or not.
                  By default, False; meaning the files will be removed on
                  successful submission to the database.
         verbose: As the daemon reinitializes logging, the verbose argument
                  facilitates setting the verbosity from the CLI. Defaults to 0
    '''
    global sig_count
    sig_count = 0

    logger.debug('daemon_loop(niters=%d,post_process=%s,analyze=%s,retire=%s,ingest=%s,recursive=%s,keep=%s)', niters, post_process, analyze, retire, ingest, recursive, keep)

    if retire:
        if (settings.retire_jobs_ndays == 0) and (settings.retire_models_ndays == 0):
            logger.error('You have enabled retire mode for the daemon. However, settings.py has it disabled. Please set a non-zero value for "retire_jobs_ndays" and/or "retire_models_ndays". Alternatively, disable retire mode for the daemon')
            return True
        logger.info('retire mode enabled for daemon')
        logger.info('jobs will be retired after {} days'.format(settings.retire_jobs_ndays))
        logger.info('models will be retired after {} days'.format(settings.retire_models_ndays))

    if ingest:
        logger.info('ingestion mode enabled for daemon')
        logger.info('ingestion mode (path={},recursive={},keep={})'.format(ingest,recursive, keep))
        if not (path.isdir(ingest)):
            logger.error('Ingest path ({}) does not exist'.format(ingest))
            return True
        from epmtlib import suggested_cpu_count_for_submit
        ncpus = suggested_cpu_count_for_submit()
        if (ncpus > 1) and ((settings.orm != 'sqlalchemy') or (orm_db_provider() != "postgres")):
            logger.error('Parallel submit is only supported for Postgres + SQLAlchemy at present')
            return True

    if post_process:
        if ingest and settings.post_process_job_on_ingest:
            logger.error('Settings has post_process_job_on_ingest set, but post_processing was selected')
            return True
        logger.info('post-process mode enabled for daemon')
        if analyze:
            logger.info('analysis mode enabled for daemon')

    print('Starting the EPMT daemon')
    with context:
        # are we a daemon? Daemons have a PPID of 1
        # Note, this function may also have been invoked in foreground
        # mode, where are not a daemon..
        if getppid() == 1:
        # We reinitialize logging as our earlier logging choices
        # were made before we became a daemon. In particular we
        # might not have been using the file handler for logging.
            verbose = verbose or (settings.verbose if hasattr(settings, 'verbose') else 0)
            epmt_logging_init(verbose, check=False)
        
        tot_pp_jobs = 0
        tot_ua_jobs = 0
        iters = 0

        # max delay in seconds; we will subtract from this processing time
        MAX_DELAY = 10
        logger.info('starting daemon loop')
        while (True):
            if (sig_count > 0):
                logger.warning('Terminating EPMT daemon gracefully')
                exit(0)
            # We check whether a task (such as ingest, post-processing or
            # retirement is enabled and if so, do the actions associated
            # with the task. Multiple tasks may be enabled.
            _t1 = time()
            if ingest:
                logger.debug('checking dir {} for jobs to ingest'.format(ingest))
                tgz_files = find_files_in_dir(ingest, '*.tgz', recursive = recursive)
                if tgz_files:
                    logger.info('{} .tgz files found to ingest'.format(len(tgz_files)))
                    epmt_submit(tgz_files, dry_run = False, ncpus=ncpus, remove_file=not(keep))
            if post_process:
                # unprocessed jobs (these are jobs on whom post-processing
                # pipeline hasn't run; these are different from jobs on whom
                # the analysis pipeline hasn't run)
                # Get unprocessed jobs
                # For each job
                # Post process if post-process
                # Analyze If post-process and analyze
                # Jobs that fail, should be removed and logged
                unpdj = get_unprocessed_jobs()
                logger.info("%d unprocessed jobs found",len(unpdj))
                ppd_jobs = post_process_jobs(unpdj)
                # unpdj - ppd_jobs should be 0 in size, let's check
                err_ppd_jobs = list(filter(lambda i: i not in ppd_jobs, unpdj))
                tot_pp_jobs += len(ppd_jobs)
                logger.info('{0} jobs post-processed, {1} errors'.format(len(ppd_jobs),len(err_ppd_jobs)))
                # 
                # Handle unprocessed jobs, remove from unprocessed and log
                #
                if analyze:
                    # now run the analyses pipelines (outlier detection, etc)
                    ana_jobs = analyze_jobs(ppd_jobs, check=False)
                    # ppd_jobs - ana_jobs should be 0, let's check
                    err_ana_jobs = list(filter(lambda i: i not in ana_jobs, ppd_jobs))
                    tot_ua_jobs += len(ana_jobs)
                    logger.info('{0} jobs analyzed, {1} errors'.format(len(ana_jobs),len(err_ana_jobs)))
                    #
                    # Handle unanalyzed jobs, log (don't remove)
                    #
                if retire:
                    epmt_retire()

            iters += 1
            if niters and (iters > niters):
                logger.debug('ending daemon loop, as requested iterations completed')
                break
            _loop_time = (time() - _t1)
            delay = MAX_DELAY - _loop_time
            if delay > 0:
                logger.debug('sleeping for {0:.3f} sec'.format(delay))
                sleep(delay)
            else:
                logger.warning("daemon loop took {0} seconds. No sleep for me!".format(_loop_time))
        exit(0)

def signal_handler(signum, frame):
    global sig_count
    if sig_count > 0:
        # logger.warning('Received multiple signals to terminate. Terminating now!')
        exit(signum)
    else:
        # let the daemon loop know that we should exit gracefully at the
        # very next opportunity
        # logger.warning('Received signal; will terminate shortly')
        sig_count = 1
    return None

