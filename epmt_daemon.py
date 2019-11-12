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
    from time import sleep
    while True: sleep(1)
