# from __future__ import print_function
from getpass import getuser
from os import path, kill, unlink, getppid
from sys import exit, stdin, stdout, stderr
from time import sleep, time
from daemon import DaemonContext, pidfile
from signal import SIGHUP, SIGTERM, SIGQUIT, SIGINT, SIGUSR1
import logging
logger = logging.getLogger(__name__)  # you can use other name

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
sig_count = 0


def is_daemon_running(pidf=PID_FILE):
    from epmt.epmtlib import check_pid
    logger = logging.getLogger(is_daemon_running.__name__)
    logger.debug("Looking for file %s to fetch daemon pid", pidf)
    try:
        with open(pidf, 'r') as f:
            pid = f.read().strip()
        logger.debug('Found daemon lockfile with PID({0})'.format(pid))
#    except IOError:
#        return -1
    except Exception as e:
        logger.debug(str(e))
        return False, -1
    if int(pid) < 0:
        logger.error('PID %d for daemon is less than 0, this cant be true', int(pid))
        return False, -1
    stat, msg = check_pid(int(pid))
    if not stat:
        #        logger.warning("PID %d for daemon doesn't seem alive: %s",int(pid),msg)
        logger.error("You should check PID {0} and consider removing the stale lock file {1}.".format(int(pid), pidf))
        return False, -1
    return True, int(pid)


def start_daemon(foreground=False, pidf=PID_FILE, **daemon_args):
    logger = logging.getLogger(start_daemon.__name__)
    stat, pid = is_daemon_running(pidf)
    if stat:
        logger.error(
            'Daemon may be still running at pid {0}. If not, please remove the lock file {1} and try again'.format(
                pid,
                pidf))
        return (-1)
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
        logger.info('Using lock file {0} for the EPMT daemon'.format(pidf))
        # ensure logging uses the same file-descriptors and they are preserved across the fork
        logger_files = []
        try:
            for handler in logging.root.handlers:
                fileno = handler.stream.fileno()
                logger_files.append(fileno)
            if logger_files:
                context.files_preserve = logger_files
        except BaseException:
            logger.warning('could not get file descriptor for logging in daemon')
    context.signal_map = {}
    # set up signal handlers
    for sig in [SIGHUP, SIGTERM, SIGQUIT, SIGINT, SIGUSR1]:
        context.signal_map[sig] = signal_handler

    # start daemon
    daemon_loop(context, **daemon_args)
    return 0


def stop_daemon(pidf=PID_FILE):
    logger = logging.getLogger(stop_daemon.__name__)
    stat, pid = is_daemon_running(pidf)
    if stat:
        logger.info('Sending SIGUSR1 signal to EPMT daemon PID {0}'.format(pid))
        try:
            print("Sending signal to EPMT daemon pid " + str(pid))
            kill(pid, SIGUSR1)
        except Exception as e:
            logger.error('Error sending SIGUSR1 to process PID {0}: {1}'.format(pid, str(e)))
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
    logger = logging.getLogger(print_daemon_status.__name__)
    stat, pid = is_daemon_running(pidf)
    if not stat:
        print('EPMT daemon not running, start with "epmt daemon --start"')
        return -1
    else:
        print('EPMT daemon running PID {0}. stop with "epmt daemon --stop"'.format(pid))
    return 0

# if niters is set, then the daemon loop will end after 'niters' iterations
# otherwise loop forever or until we get interrupted by a signal


def daemon_loop(context, niters=0, post_process=True, analyze=True, retire=False,
                ingest=False, recursive=False, keep=False, move_away=True, verbose=0):
    '''
    Runs a daemon loop niters times, performing enabled actions
    such as post-processing, ingestion, etc.

         context: Python daemon context
          niters: Number of times to run the daemon loop, 0 = forever
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

    logger = logging.getLogger(daemon_loop.__name__)
    logger.debug(
        '(context=%s,niters=%d,post_process=%s,analyze=%s,retire=%s,ingest=%s,recursive=%s,keep=%s,moveaway=%s,verbose=%d)',
        type(context),
        niters,
        post_process,
        analyze,
        retire,
        ingest,
        recursive,
        keep,
        move_away,
        verbose)

    if retire:
        if (settings.retire_jobs_ndays == 0) and (settings.retire_models_ndays == 0):
            logger.error('You have enabled retire mode for the daemon. However, settings.py has it disabled. Please set a non-zero value for "retire_jobs_ndays" and/or "retire_models_ndays". Alternatively, disable retire mode for the daemon')
            return True
        logger.info('retire mode enabled for daemon')
        logger.info('jobs will be retired after {} days'.format(settings.retire_jobs_ndays))
        logger.info('models will be retired after {} days'.format(settings.retire_models_ndays))

    if ingest:
        logger.info('ingestion mode enabled for daemon')
        logger.info(
            'ingestion mode (path={},recursive={},keep={},move_away={})'.format(
                ingest, recursive, keep, move_away))
        if not (path.isdir(ingest)):
            logger.error('Ingest path ({}) does not exist'.format(ingest))
            return True
        from epmt.epmtlib import suggested_cpu_count_for_submit
        ncpus = suggested_cpu_count_for_submit()
        from epmt.orm import orm_db_provider
        if (ncpus > 1) and ((settings.orm != 'sqlalchemy') or (orm_db_provider() != "postgres")):
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

        while (True):
            logger.info('starting daemon loop - iteration %d', iters)
            if (sig_count > 0):
                logger.info('Terminating EPMT daemon gracefully')
                return False

            # We check whether a task (such as ingest, post-processing or
            # retirement is enabled and if so, do the actions associated
            # with the task. Multiple tasks may be enabled.
            _t1 = time()

            if ingest:
                from epmt.epmtlib import find_files_in_dir
                from epmt.epmt_cmds import epmt_submit
                logger.debug('checking dir {} for jobs (*.tgz) to ingest'.format(ingest))
                tgz_files = find_files_in_dir(ingest, '*.tgz', recursive=recursive)
                if tgz_files:
                    logger.info('{} .tgz files found to ingest'.format(len(tgz_files)))
                    epmt_submit(
                        tgz_files,
                        ncpus=ncpus,
                        dry_run=False,
                        keep_going=True,
                        remove_on_success=not (keep),
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
                unpdj = get_unprocessed_jobs()
                logger.info("%d unprocessed jobs found", len(unpdj))
                ppd_jobs = post_process_jobs(unpdj, check=False)
                # unpdj - ppd_jobs should be 0 in size, let's check
                err_ppd_jobs = list(filter(lambda i: i not in ppd_jobs, unpdj))
                tot_pp_jobs += len(ppd_jobs)
                logger.info('{0} jobs post-processed, {1} errors'.format(len(ppd_jobs), len(err_ppd_jobs)))

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
                    logger.info('{0} jobs analyzed, {1} errors'.format(len(ana_jobs), len(err_ana_jobs)))

                    #
                    # Handle unanalyzed jobs, log (don't remove)
                    #

                if retire:
                    from epmt.epmt_cmd_retire import epmt_retire
                    epmt_retire()

            iters += 1
            _loop_time = (time() - _t1)
            delay = MAX_DELAY - _loop_time
            #if (niters > 0) and (iters >= niters):
            if 0 < niters <= iters:
                logger.debug('ending daemon loop, as requested %d iterations completed', niters)
                break
            if delay > 0:
                logger.debug('sleeping for {0:.3f} sec'.format(delay))
                sleep(delay)
            else:
                logger.warning("daemon loop took {0} seconds. No sleep for me!".format(_loop_time))
        return False


def signal_handler(signum, frame):
    global sig_count
    if sig_count > 0:
        logger.warning('Received multiple signals to terminate. Terminating now!')
        exit(signum)
    else:
        # let the daemon loop know that we should exit gracefully at the
        # very next opportunity
        logger.info('Received signal; will terminate shortly')
        sig_count = 1
    return None
