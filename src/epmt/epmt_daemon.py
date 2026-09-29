"""
EPMT daemon module - handles background daemon functionality.
"""

from getpass import getuser
from os import path, kill, unlink
from sys import exit as sysexit
from sys import stdin, stdout, stderr
from time import sleep, time
from signal import SIGHUP, SIGTERM, SIGQUIT, SIGINT, SIGUSR1
from logging import getLogger

try:
    from daemon import DaemonContext, pidfile
except ImportError:
    # daemon module not available
    DaemonContext = None
    pidfile = None

logger = getLogger(__name__)

# DO NOT IMPORT ANYTHING FROM ANY EPMT FILES HERE
# **** IT WILL BREAK WHEN THE DAEMON FORKS ****
# ALL IMPORTS SHOULD BE HANDLED IN DAEMON LOOP
# **** AFTER ****
# THE DAEMON OR NULL CONTEXT ENTERED

# This should be in settings somewhere
PID_FILE = '/tmp/epmt.pid.' + getuser()

# we use this global so we can force exit if
# more than one signal is received. Otherwise,
# in each iteration of the daemon we will check if
# we received a signal earlier and stop gracefully.
# A global is unfortunately necessary as this variable
# is shared between the signal handler and the daemon loop
SIG_COUNT = 0


def is_daemon_running(pidf=PID_FILE):
    """
    Check if daemon is running based on PID file.
    """
    from epmt.epmtlib import check_pid

    logger.debug("Looking for file %s to fetch daemon pid", pidf)
    try:
        with open(pidf, 'r', encoding='utf-8') as f:
            pid = f.read().strip()
        logger.debug('Found daemon lockfile with PID(%s)', pid)
    except Exception as e:
        logger.debug(str(e))
        return False, -1
    if int(pid) < 0:
        logger.error('PID %d for daemon is less than 0, this cant be true', int(pid))
        return False, -1
    stat, _msg = check_pid(int(pid))
    if not stat:
        logger.error("You should check PID %d and consider removing the stale lock file %s.",
                            int(pid), pidf)
        return False, -1
    return True, int(pid)


def _preserve_logger_file_descriptors(context, logger_name='epmt'):
    """
    Preserve open logger streams across ``DaemonContext`` setup.

    ``python-daemon`` closes every open file descriptor except stdio and any
    descriptors listed in ``files_preserve`` when the context is entered. If
    logging has already been initialized, file-based handlers need to be added
    to that preserve list so later log writes do not hit a closed stream.
    """
    logger_files = list(getattr(context, 'files_preserve', []) or [])
    for handler in getLogger(logger_name).handlers:
        stream = getattr(handler, 'stream', None)
        if stream is None:
            continue
        try:
            fileno = stream.fileno()
        except (AttributeError, OSError, ValueError):
            continue
        logger_files.append(fileno)

    if logger_files:
        context.files_preserve = list(dict.fromkeys(logger_files))


def start_daemon(foreground=False, pidf=PID_FILE, **daemon_args):
    """
    Start the daemon process.
    """
    stat, pid = is_daemon_running(pidf)
    if stat:
        logger.error(
            'Daemon may be still running at pid %d. If not, please remove the lock file %s and try again',
            pid, pidf)
        return -1

    # set up signal handlers
    # from signal import SIGHUP, SIGTERM, SIGQUIT, SIGINT, SIGUSR1, signal
    # for sig in [SIGHUP, SIGTERM, SIGQUIT, SIGINT, SIGUSR1]:
    #     signal(sig, signal_handler)
    # logger.debug('Finished setting up signal handlers')

    logger.debug("setting up background with DaemonContext")
    context = DaemonContext()
    if foreground:
        context.detach_process = False
        context.stdin = stdin
        context.stdout = stdout
        context.stderr = stderr
    else:
        context.detach_process = True
        context.pidfile = pidfile.TimeoutPIDLockFile(pidf)
        logger.info('Using lock file %s for the EPMT daemon', pidf)
    # ensure logging uses the same file descriptors after entering the daemon
    # context, even in foreground mode where logging was already initialized.
    _preserve_logger_file_descriptors(context)
    context.signal_map = {}

    # set up signal handlers
    for sig in [SIGHUP, SIGTERM, SIGQUIT, SIGINT, SIGUSR1]:
        context.signal_map[sig] = signal_handler

    # start daemon
    daemon_loop(context, **daemon_args)
    return 0


def stop_daemon(pidf=PID_FILE):
    """
    Stop the daemon process.
    """
    stat, pid = is_daemon_running(pidf)
    if stat:
        logger.info('Sending SIGUSR1 signal to EPMT daemon PID %s', pid)
        try:
            print("Sending signal to EPMT daemon pid " + str(pid))
            kill(pid, SIGUSR1)
        except Exception as e:
            logger.error('Error sending SIGUSR1 to process PID %s: %s', pid, e)
            return -1
    else:
        logger.error('EPMT daemon not running, start with "epmt daemon --start"')
        return -1

    # normally the lock file is removed already. Just in case it isn't
    # perhaps because the process had been killed with SIGKILL, we will
    # remove the stale lock file. Make sure to ignore any exceptions,
    # since you can count on getting an IOError for file not found
    try:
        unlink(pidf)
    except BaseException:
        pass
    return 0


def print_daemon_status(pidf=PID_FILE):
    """
    Print status of daemon.
    """
    stat, pid = is_daemon_running(pidf)
    if not stat:
        print('EPMT daemon not running, start with "epmt daemon --start"')
        return -1
    print(f'EPMT daemon running PID {pid}. stop with "epmt daemon --stop"')

    return 0


# set maxiters=1 to help with debugging
def daemon_loop(context, maxiters=0, post_process=True, analyze=True, retire=False,
                ingest=False, recursive=False, keep=False, move_away=True, verbose=0):
    '''
    Runs a daemon loop maxiters times, performing enabled actions
    such as post-processing, ingestion, etc.

    if maxiters is set, then the daemon loop will end after 'maxiters' iterations
    otherwise loop forever or until we get interrupted by a signal

         context: Python daemon context
        maxiters: Number of times to run the daemon loop, 0 = forever
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
       move_away: Only meaningful when ingest is set. It indicates whether
                  on failed ingest the file should be moved away to the value
                  in settings.failed_ingest_dir
                  By default, True; meaning the files will be moved away on
                  failed submission to the database.
         verbose: As the daemon reinitializes logging, the verbose argument
                  facilitates setting the verbosity from the CLI. Defaults to 0
    '''
    import epmt.epmt_settings as settings
    from epmt.epmtlib import init_settings
    init_settings(settings)  # normally this is done when you import epmt_query

    global sig_count
    sig_count = 0

    logger.debug(
        '(context=%s,maxiters=%d,post_process=%s,analyze=%s,'
        'retire=%s,ingest=%s,recursive=%s,keep=%s,move_away=%s,verbose=%d)',
        type(context),
        maxiters,
        post_process,
        analyze,
        retire,
        ingest,
        recursive,
        keep,
        move_away,
        verbose)

    if retire:
        if settings.retire_jobs_ndays == 0 and settings.retire_models_ndays == 0:
            logger.error('You have enabled retire mode for the daemon. However, settings.py has it disabled. '
                         'Please set a non-zero value for "retire_jobs_ndays" and/or "retire_models_ndays". '
                         'Alternatively, disable retire mode for the daemon')
            return True
        logger.info('retire mode enabled for daemon')
        logger.info('jobs will be retired after %s days', settings.retire_jobs_ndays)
        logger.info('models will be retired after %s days', settings.retire_models_ndays)

    if ingest:
        logger.info('ingestion mode enabled for daemon')
        logger.info('ingestion mode (path=%s,recursive=%s,keep=%s,move_away=%s)',
                    ingest, recursive, keep, move_away)
        if not path.isdir(ingest):
            logger.error('Ingest path (%s) does not exist', ingest)
            return True

        from epmt.epmtlib import suggested_cpu_count_for_submit
        ncpus = suggested_cpu_count_for_submit()

        from epmt.orm import orm_db_provider
        if ncpus > 1 and ( settings.orm != 'sqlalchemy' or orm_db_provider() != "postgres" ):
            logger.warning('Parallel submit only supported for Postgres+SQLAlchemy, using 1 cpu')
            ncpus = 1

    if post_process:
        if ingest and settings.post_process_job_on_ingest:
            logger.error('Settings has post_process_job_on_ingest set, but post_processing was selected')
            return True
        logger.info('post-process mode enabled for daemon')
        if analyze:
            logger.info('analysis mode enabled for daemon')

    print('Starting the EPMT daemon')

    with context:
        # We reinitialize logging as our earlier logging choices
        # were made before we became a daemon. In particular we
        # might not have been using the file handler for logging.
        if hasattr(context, 'detach_process') and context.detach_process:
            #import epmt.epmt_settings as settings
            from epmt.epmtlib import epmt_logging_init
            verbose = verbose or (settings.verbose if hasattr(settings, 'verbose') else 0)
            epmt_logging_init(verbose, check=False)

        # max delay in seconds; we will subtract from this processing time
        # should be in settings instead!
        MAX_DELAY = 60

        # Locals
        tot_pp_jobs = 0
        tot_ua_jobs = 0
        iters = 0

        while True:
            logger.info('starting daemon loop - iteration %d', iters)
            if sig_count > 0:
                logger.info('Terminating EPMT daemon gracefully')
                return False

            # We check whether a task (such as ingest, post-processing or
            # retirement is enabled and if so, do the actions associated
            # with the task. Multiple tasks may be enabled.
            _t1 = time()

            if ingest:
                from epmt.epmtlib import find_files_in_dir
                from epmt.epmt_cmds import epmt_submit
                logger.debug('checking dir %s for jobs (*.tgz) to ingest', ingest)
                tgz_files = find_files_in_dir(ingest, '*.tgz', recursive=recursive)
                if tgz_files:
                    logger.info('%s .tgz files found to ingest', len(tgz_files))
                    epmt_submit(
                        tgz_files,
                        ncpus=ncpus,
                        dry_run=False,
                        keep_going=True,
                        remove_on_success=not keep,
                        move_on_failure=move_away)

            if post_process:
                # unprocessed jobs (these are jobs on whom post-processing
                # pipeline hasn't run; these are different from jobs on whom
                # the analysis pipeline hasn't run)
                # Get unprocessed jobs
                # For each job
                # Post process if post-process
                # Analyze If post-process and analyze
                # Jobs that fail, should be removed and logged
                from epmt.epmt_query import get_unprocessed_jobs, post_process_jobs
                unprocd_jobs = get_unprocessed_jobs()
                logger.info("%d unprocessed jobs found", len(unprocd_jobs))
                ppd_jobs = post_process_jobs(unprocd_jobs, check=False)
                # unprocd_jobs - ppd_jobs should be 0 in size, let's check
                err_ppd_jobs = list(filter(lambda i: i not in ppd_jobs, unprocd_jobs))
                tot_pp_jobs += len(ppd_jobs)
                logger.info('%s jobs post-processed, %s errors', len(ppd_jobs), len(err_ppd_jobs))

                #
                # Handle unprocessed jobs, remove from unprocessed and log
                #

                if analyze:
                    from epmt.epmt_query import analyze_jobs
                    # now run the analyses pipelines (outlier detection, etc)
                    ana_jobs = analyze_jobs(ppd_jobs, check=False)
                    # ppd_jobs - ana_jobs should be 0, let's check
                    err_ana_jobs = list(filter(lambda i: i not in ana_jobs, ppd_jobs))
                    tot_ua_jobs += len(ana_jobs)
                    logger.info('%s jobs analyzed, %s errors', len(ana_jobs), len(err_ana_jobs))

                    #
                    # Handle unanalyzed jobs, log (don't remove)
                    #

                if retire:
                    from epmt.epmt_cmd_retire import epmt_retire
                    epmt_retire()

            iters += 1
            _loop_time = time() - _t1
            delay = MAX_DELAY - _loop_time
            if 0 < maxiters <= iters:
                logger.debug('ending daemon loop, as requested %d iterations completed', maxiters)
                break
            if delay > 0:
                logger.debug('sleeping for %.3f sec', delay)
                sleep(delay)
            else:
                logger.warning('daemon loop took %s seconds. No sleep for me!', _loop_time)
        return False


def signal_handler(signum, frame):
    global sig_count
    if sig_count > 0:
        logger.warning('Received multiple signals to terminate. Terminating now!')
        sysexit(signum)

    # let the daemon loop know that we should exit gracefully at the
    # very next opportunity
    logger.info('Received signal; will terminate shortly')
    sig_count = 1
    ## inl: actually a useless return? signal stuff makes me anxious
    ##      check back here again when possible TODO
    #return None
