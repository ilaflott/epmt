"""
EPMT Misc. Library
==================

This module provides miscellaneous functions such as those needed
for manipulating data structures.
"""
from functools import wraps
from time import time
from logging import getLogger, DEBUG, ERROR, INFO, WARNING, CRITICAL
from os import environ, unlink, devnull, getuid
from contextlib import contextmanager
from subprocess import call
from json import dumps, loads
from pwd import getpwuid

from io import StringIO


# semantic version
# first element is the major version number
# second element is the minor version number
# third element is the patch or bugfix number
# Since we are saving as a tuple you can do a simple
# compare of two version tuples and python will do the right thing
_version = (4,11,0)

def version():
    return _version

def version_str(terse = False):
    v = ".".join([str(i) for i in _version])
    return v if terse else "EPMT {0}".format(v)

def get_username():
    return getpwuid( getuid() )[ 0 ]

# if check is set, then we will bail if logging has already been initialized
def epmt_logging_init(intlvl = 0, check = False, log_pid = False):
    import logging
    import epmt.epmt_settings as settings

    if check and hasattr(epmt_logging_init, 'initialized'):
        return
    epmt_logging_init.initialized = True
    if intlvl is None:
        intlvl = 0
    intlvl = int(intlvl)
    if intlvl < -1:
        level = CRITICAL # 50
    elif intlvl == -1:
        level = ERROR # 40
    elif intlvl == 0:
        level = WARNING # 30
    elif intlvl == 1:
        level = INFO # 20
    else: #intlvl >= 2:
        level = DEBUG # 10

    # Set level and remove all existing handlers
    #rootLogger = getLogger(__name__) # thank you! @ ericzhou13
    rootLogger = getLogger()
    rootLogger.debug("epmt_logging_init(%d,%s,%s): %d handlers",intlvl,check,log_pid,len(rootLogger.handlers))
    for handler in rootLogger.handlers:
        rootLogger.removeHandler(handler)
    rootLogger.setLevel(level)

    # only log to file if stdout is not a tty
    from sys import stdout
    if not stdout.isatty():
        # basicConfig(filename='epmt.log', filemode='a', level=level)
        logFormatter = logging.Formatter("[%(asctime)-19.19s, %(process)6d] %(levelname)-7.7s %(name)s:%(message)s")
        fileHandler = logging.FileHandler(settings.logfile)
        fileHandler.setFormatter(logFormatter)
        fileHandler.setLevel(level)
        rootLogger.debug("epmt_logging_init(): not_a_tty: adding handler for settings.logfile=%s",settings.logfile)
        rootLogger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler()
    consoleFormatter = logging.Formatter(
        "[%(asctime)-19.19s, %(process)d] %(levelname)7.7s: %(name)s: %(message)s" if log_pid else "%(asctime)-19.19s %(levelname)7.7s: %(name)s: %(message)s")
    consoleHandler.setFormatter(consoleFormatter)
    rootLogger.addHandler(consoleHandler)

    # matplotlib generates a ton of debug messages
    mpl_logger = logging.getLogger('matplotlib')
    mpl_logger.setLevel(logging.WARNING)

    # numba.byteflow generates a ton of debug messages
    numba_logger = logging.getLogger('numba')
    numba_logger.setLevel(logging.WARNING)

    # ipython's parso logger has too many debug messages
    parso_logger = logging.getLogger('parso')
    parso_logger.setLevel(logging.WARNING)

    alembic_logger = logging.getLogger('alembic')
    alembic_logger.setLevel(level)

    # sqlalchemy tends to be more verbose than we'd like it.
    # at INFO level it shows a lot. So, when the user requests
    # debug (-v -v), then we'd like to show at INFO level.
    # And, when the user requests normal (-v), we'd not like
    # to show the sqlalchemy's INFO level messages (but instead
    # a level higher).
    sqlalchemy_logger = logging.getLogger('sqlalchemy')
    #sqlalchemy_logger.setLevel(level+10)
    #sqlalchemy_logger.setLevel(level+20)
    sqlalchemy_logger.setLevel(level+30)

def init_settings(settings):
    if hasattr(init_settings, 'initialized'): return
    init_settings.initialized = True

    logger = getLogger('init_settings')
    err_msg = ""

    if environ.get("PAPIEX_OUTPUT"):
        logger.warning("PAPIEX_OUTPUT variable should not be defined, it will be ignored")
    if environ.get("PAPIEX_OPTIONS"):
        logger.warning("PAPIEX_OPTIONS variable should not be defined, it will be ignored")

    for k in [ "provider", "user", "password", "host", "dbname", "filename", "url" ]:
        name = "EPMT_DB_"+ k.upper()
        t = environ.get(name)
        if t:
            logger.info("%s found, overriding setting from %s:%s to %s:%s",name,k,settings.db_params.get(k, ''),k,t)
            settings.db_params[k] = t

    if not hasattr(settings,"epmt_output_prefix"):
        err_msg += "\n - missing settings.epmt_output_prefix"
    if not settings.epmt_output_prefix.endswith("/"):
        logger.warning("settings.epmt_output_prefix should end in a /")
        settings.epmt_output_prefix += "/"
    if not hasattr(settings, 'job_tags_env'):
        logger.warning("missing settings.job_tags_env")
        settings.job_tags_env = 'EPMT_JOB_TAGS'
    if not hasattr(settings, 'jobid_env_list'):
        logger.warning("missing settings.jobid_env_list")
        settings.jobid_env_list = [ "SLURM_JOB_ID", "SLURM_JOBID", "PBS_JOB_ID" ]
    if not hasattr(settings, 'verbose'):
        logger.warning("missing settings.verbose")
        settings.verbose = 1
    if not hasattr(settings, 'logfile'):
        logger.warning("missing settings.logfile")
        settings.verbose = 'epmt.log'
    if not hasattr(settings, 'stage_command'):
        logger.warning("missing settings.stage_command ")
        settings.stage_command = "cp"
    if not hasattr(settings, 'stage_command_dest'):
        logger.warning("missing settings.stage_command_dest")
        settings.stage_command_dest = "./"
    if not hasattr(settings, 'input_pattern'):
        logger.warning("missing settings.input_pattern")
        settings.input_pattern = "*-papiex-*-[0-9]*.csv"
    if not hasattr(settings, 'per_process_fields'):
        logger.warning("missing settings.per_process_fields")
        settings.per_process_fields = ["tags","hostname","exename","path","args","exitcode","pid","generation","ppid","pgid","sid","numtids"]
    if not hasattr(settings, 'skip_for_thread_sums'):
        logger.warning("missing settings.skip_for_thread_sums")
        settings.skip_for_thread_sums = ["tid", "start", "end", "num_threads", "starttime"]
    if not hasattr(settings, 'outlier_thresholds'):
        logger.warning("missing settings.outlier_thresholds")
        settings.outlier_thresholds = { 'modified_z_score': 2.5, 'iqr': [20,80], 'z_score': 3.0 }
    if not hasattr(settings, 'outlier_features'):
        logger.warning("missing settings.outlier_features")
        settings.outlier_features = ['duration', 'cpu_time', 'num_procs']
    if not hasattr(settings, 'outlier_features_blacklist'):
        logger.warning("missing settings.outlier_features_blacklist")
        settings.outlier_features_blacklist = ['env_dict', 'tags', 'info_dict', 'env_changes_dict', 'annotations', 'analyses', 'jobid', 'jobname', 'user', 'all_proc_tags']
    if not hasattr(settings, 'retire_jobs_ndays'):
        logger.warning("missing settings.retire_jobs_ndays")
        settings.retire_jobs_ndays = 0
    if not hasattr(settings, 'retire_models_ndays'):
        logger.warning("missing settings.retire_models_ndays")
        settings.retire_models_ndays = 0
    if not hasattr(settings, 'bulk_insert'):
        logger.warning("missing settings.bulk_insert")
        settings.bulk_insert = False
    if (settings.orm != 'sqlalchemy' and settings.bulk_insert):
        err_msg += '\n - bulk_insert is only supported by sqlalchemy'
    if not hasattr(settings, 'post_process_job_on_ingest'):
        logger.warning("missing settings.post_process_job_on_ingest")
        settings.post_process_job_on_ingest = False
        if (settings.orm == 'sqlalchemy'):
            settings.post_process_job_on_ingest = True
    if settings.post_process_job_on_ingest and settings.orm != 'sqlalchemy':
        logger.warning("settings.post_process_job_on_ingest = True only supported for sqlalchemy, now False")
        settings.post_process_job_on_ingest = False
    if not hasattr(settings, 'lazy_compute_process_tree'):
        logger.warning("missing settings.lazy_compute_process_tree")
        settings.lazy_compute_process_tree = True
    if not hasattr(settings, 'epmt_settings_kind'):
        logger.warning('settings missing epmt_settings_kind field. filling in ourselves.')
        settings.epmt_setttings_kind = 'filled_by_epmtlib_init_settings'
    if not hasattr(settings, 'db_params'):
        err_msg += "\n - missing settings.db_params"
    if err_msg:
        err_msg = "The following error(s) were detecting in your settings: " + err_msg
        logger.error(err_msg)
        raise ValueError(err_msg)
    return True

def run_shell_cmd(*cmd):
    nf = open(devnull, 'w')
    rc = call(cmd, stdout=nf, stderr=nf)
    return rc

def cmd_exists(cmd):
    if not cmd: return False
    from shutil import which
    return which(cmd) is not None

def safe_rm(f):
    if not(f): return False
    try:
        unlink(f)
        return True
    except Exception:
        pass
    return False

def timing(f):
    logger = getLogger(__name__)
    @wraps(f)
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        if result:
            logger.debug('%r took: %2.5f sec' % (f.__name__, te-ts))
        return result
    return wrap

@contextmanager
def capture():
    '''
    This function has a bug because it does not work with subprocess.run().
    Needs to be fixed #TODO
    '''
    import sys
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err

def tag_from_string(s, delim = ';', sep = ':', tag_default_value = '1'):
    '''
    we assume tag is of the format:
     "key1:value1 ; key2:value2"
    where the whitespace is optional and discarded. The output would be:
    { "key1": value1, "key2": value2 }
    
    We can also handle the case where a value is not set for
    a key, by assigning a default value for the key
    For example, for the input:
    "multitheaded;app=fft" and a tag_default_value="1"
    the output would be:
    { "multithreaded": "1", "app": "fft" }
    
    Note, both key and values will be strings and no attempt will be made to
    guess the type for integer/floats
    '''
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore",category=DeprecationWarning)
        # from pony.orm.ormtypes import TrackedDict
#    if type(s) in (dict, TrackedDict): return s
    if type(s) == dict: return s
    if not s: return (None if s == None else {})

    logger = getLogger(__name__)
    tag = {}
    for t in s.split(delim):
        t = t.strip()
        if sep in t:
            try:
                (k,v) = t.split(sep)
                k = k.strip()
                v = v.strip()
                tag[k] = v
            except Exception as e:
                logger.warning('ignoring key/value pair as it has an invalid format: {0}'.format(t))
                logger.warning("%s",e)
                continue
        else:
            # tag is not of the format k:v
            # it's probably a simple label, so use the default value for it
            tag[t] = tag_default_value
    return tag

def tag_dict_to_string(tag, delim = ';', sep = ':'):
    '''
    Converts a dictionary tag to a string
    '''
    if type(tag) == str:
        return tag
    return delim.join([ "{}{}{}".format(k, sep, tag[k]) for k in sorted(tag.keys()) ])

def tags_list(tags):
    """
    returns a list of tags, where each tag is a dict.
    the input can be a list of strings or a single string.
    each string will be converted to a dict
    """
    # do we have a single tag in string or dict form?
    if isString(tags):
        tags = [tag_from_string(tags)]
    elif type(tags) == dict:
        tags = [tags]
    tags = [tag_from_string(t) if isString(t) else t for t in tags]
    return tags

# Returns True if at least one dictionary in L is contained by d
# where containment is defined as all keys of the containee
# are in the container with matching values. Container may have
# additional key/values.
# For example:
# for input ({'abc':100, 'def':200}, [{'hello': 50}, {'abc':100}]
# we get True
def dict_in_list(d, L):
    for item in L:
        flag = True
        for (k,v) in item.items():
            if (not k in d) or not(d[k] == v):
                flag = False
        if (flag): return True
    return False


def sum_chk_overflow(x, y):
    z = x + y
    if (abs(z) > (2 ** 31 - 1)):
       z = float(x) + float(y)
    return z

def sum_dicts(x, y):
    """
    return the sum of keys across two dictionaries
        x = {'both1':1, 'both2':2, 'only_x': 100 }
        y = {'both1':10, 'both2': 20, 'only_y':200 }
        {'only_y': 200, 'both2': 22, 'both1': 11, 'only_x': 100}
    """
    return { k: x.get(k, 0) + y.get(k, 0) for k in set(x) | set(y) }

def sum_dicts_list(dicts, exclude=[]):
    all_keys = set()
    for d in dicts:
        all_keys |= set(d)
    all_keys -= set(exclude)
    sum_dict = {}
    for k in all_keys:
        sum_dict[k] = 0
        for d in dicts:
            sum_dict[k] += d.get(k, 0)
    return sum_dict

# from list of dictionaries, get the unique ones
# exclude keys is an optional list of keys that are removed
# from
def unique_dicts(dicts, exclude_keys=[]):
    new_dicts = []
    if exclude_keys:
        for d in dicts:
            new_d = { x: d[x] for x in d if not x in exclude_keys }
            new_dicts.append(new_d)
    else:
        new_dicts = dicts
    # the numpy approach doesn't work in python 3
    #from numpy import unique, array
    #return unique(array(new_dicts)).tolist()

    # the commented code below changes the input ordering and makes
    # the returned list ordering different in python 2/3
    # return list(map(dict, frozenset(frozenset(d.items()) for d in new_dicts)))

    # here the code below gives a deterministic dentical ordering for python 2/3
    all_dicts_set = set()
    ordered_dicts = []
    for d in new_dicts:
        x = frozenset([(k,d[k]) for k in sorted(d.keys())])
        if not x in all_dicts_set:
            all_dicts_set.add(x)
            ordered_dicts.append(d)
    return ordered_dicts

# fold a list of dictionaries such as:
# INPUT: [{'abc': 100, 'def': 200}, {'abc': 150, 'ghi': 10}
# OUTPUT: { 'abc': [100, 150], 'def': 200, 'ghi': 10 }
def fold_dicts(dicts):
    folded_dict = {}
    for d in dicts:
        for (k,v) in d.items():
            if not (k in folded_dict):
                folded_dict[k] = set()
            folded_dict[k].add(v)
    return { k: list(v) if len(v) > 1 else v.pop() for (k,v) in folded_dict.items() }


# given a list of dictionaries, we aggregate like fields across the dictionaries
# but only when they share the same value for 'key'
# The 'exclude' fields will be skipped and not present in the output.
# Example:
#  d = [{'jobid': "3451", 'tags': {'op': 'hsmget'}, 'duration': 1000},
#       {'jobid': "1251", 'tags': {'op': 'hsmget'}, 'duration': 2000},
#       {'jobid': "3451", 'tags': {'op': 'gcp'}, 'duration': 100},
#       {'jobid': "1251", 'tags': {'op': 'gcp'}, 'duration': 200}]
#
#  group_dicts_by_key(d, key='tags', exclude = ['job', 'jobid'])
#  would return:
#  [{'tags': {'op': 'hsmget'}, duration: 3000},
#   {'tags': {'op': 'gcp'},  duration: 300}]
def group_dicts_by_key(dicts, key = 'tags', exclude = []):
    groups = {}
    for d in dicts:
        k = dumps(d[key], sort_keys=True)
        if not k in groups:
            groups[k] = []
        groups[k].append(d)
    exclude.append(key)
    out = []
    for k in sorted(groups.keys()):
        sum_dict = sum_dicts_list(groups[k], exclude)
        key_val = loads(k)
        sum_dict[key] = key_val
        out.append(sum_dict)
    return out



def isString(s):
    return isinstance(s, ("".__class__, u"".__class__))
def check_int(s):
    if s[0] in ('-', '+'):
        return s[1:].isdigit()
    return s.isdigit()
def check_boolean(s):
    if s.upper() in ('TRUE', 'FALSE'):
        return True
    return False
def check_none(s):
    if s.upper() in ('NONE'):
        return True
    return False

# Checks on a few types
# strict doesn't let anything in other than x=y
def kwargify(list_of_str, strict=False):
    myDict = {}
    jobs = []
    for s in list_of_str:
        if not "=" in s and not strict:
            jobs.append(s)
        else:
            a, b = s.split('=')
            if strict and (not a or not b):
                continue
            if check_int(b):
                myDict[a] = int(b)
            elif check_boolean(b):
                myDict[a] = bool(b)
            elif check_none(b):
                myDict[a] = None
            else: #string
                myDict[a] = b
    if myDict.get('jobs') == None and jobs and not strict:
        myDict['jobs'] = jobs
    return myDict

# this function recursively converts a dict of byte k/v pairs to
# strings. It's primarily of use when converting unpickled data in
# python 3 from data pickled using python 2
def conv_dict_byte2str(bytes_dict):
    str_dict = {}
    for key, value in bytes_dict.items():
        if type(key) == bytes:
            key = key.decode("utf-8")
        if type(value) == bytes:
            str_dict[key] = value.decode("utf-8")
        elif type(value) == dict:
            str_dict[key] = conv_dict_byte2str(value)
        else:
            str_dict[key] = value
    return str_dict

# returns a hashable dict in the form of a frozenset of dict items
# ordered by dict keys
def frozen_dict(d):
    l = [(str(k), str(d[k]) if isString(d[k]) else d[k]) for k in d.keys()]
    return frozenset(l)

# return a stringified version of the dictionary
def str_dict(d):
    new_dict = { str(k): str(v) if isString(v) else v for k, v in d.items() }
    return dumps(new_dict, sort_keys=True)

def stringify_dicts(dicts):
    return [ str_dict(d) for d in dicts ]


class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

# given a list of overlapping intervals this will return a sorted
# list of merged intervals. See,
# https://stackoverflow.com/questions/43600878/merging-overlapping-intervals
#
# For e.g.,
# input: [[-25, -14], [-21, -16], [-20, -15], [-10, -7], [-8, -5], [-6, -3], [2, 4], [2, 3], [3, 6], [12, 15], [13, 18], [14, 17], [22, 27], [25, 30], [26, 29]]
# output: [[-25, -14], [-10, -3], [2, 6], [12, 18], [22, 30]]
def merge_intervals(intervals):
     intervals.sort(key=lambda interval: interval[0])
     merged = [intervals[0]]
     for current in intervals:
         previous = merged[-1]
         if current[0] <= previous[1]:
             previous[1] = max(previous[1], current[1])
         else:
             merged.append(current)
     return merged

# checks the dictionary (d) for keys in sequence
# and returns the value for the first key found
# Returns None if no key matched
def get_first_key_match(d, *keys):
    for k in keys:
        if k in d:
            return d[k]
    return None

# Remove those with _ at beginning and blacklist
def dict_filter(kvdict, blacklisted_keys, remove_underscores = True):
    d = { k: kvdict[k] for k in kvdict.keys() if k not in blacklisted_keys }
    if remove_underscores:
        d = { k: d[k] for k in d.keys() if not k.startswith('_') }
    return d

def merge_dicts(x, y):
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z

def compare_dicts(d1, d2):
        d1_keys = set(d1.keys())
        d2_keys = set(d2.keys())
        intersect_keys = d1_keys.intersection(d2_keys)
        added = d1_keys - d2_keys
        removed = d2_keys - d1_keys
        modified = {o : (d1[o], d2[o]) for o in intersect_keys if d1[o] != d2[o]}
        same = set(o for o in intersect_keys if d1[o] == d2[o])
        return added, removed, modified, same


def get_batch_envvar(var,where):
    logger = getLogger(__name__)  # you can use other name
    key2slurm = {
        "JOB_NAME":"SLURM_JOB_NAME",
        "JOB_USER":"SLURM_JOB_USER"
        }
    if var in key2slurm.keys():
        var = key2slurm[var]
    logger.debug("looking for %s in %s",var,where)
    a=where.get(var)
    if not a:
        logger.debug("%s not found",var)
        return False

    logger.debug("%s found = %s",var,a)
    return a


def get_metadata_env_changes(metadata):
    logger = getLogger(__name__)  # you can use other name
    start_env=metadata['job_pl_env']
    stop_env=metadata['job_el_env']
    (added, removed, modified, same) = compare_dicts(stop_env, start_env)
    env_changes = {}
    # for e in same:
    #    logger.debug("Found "+e+"\t"+start_env[e])
    for e in modified:
        logger.debug("Different at stop "+e+"\t"+stop_env[e])
        env_changes[e] = stop_env[e]
    for e in removed:
        logger.debug("Deleted "+e+"\t"+start_env[e])
        env_changes[e] = start_env[e]
    for e in added:
        logger.debug("Added "+e+"\t"+stop_env[e])
        env_changes[e] = stop_env[e]
    return (env_changes, added, removed, modified, same)

# This function will do a sanity check on the metadata.
# It will mark the metadata as checked, so it's safe and
# fast to call the function (idempotently)
def check_fix_metadata(raw_metadata):
    # fast path: if we have already checked the metadata
    # we don't check it again
    if raw_metadata.get('checked'):
        return raw_metadata

    import epmt.epmt_settings as settings
    logger = getLogger(__name__)  # you can use other name
# First check what should be here
    try:
        for n in [ 'job_pl_id', 'job_pl_submit_ts', 'job_pl_start_ts', 'job_pl_env',
                   'job_el_stop_ts', 'job_el_exitcode', 'job_el_reason', 'job_el_env' ]:
            s = str(raw_metadata[n])
            assert(len(s) > 0)
    except KeyError:
        logger.error("Could not find %s in job metadata, job incomplete?",n)
        return False
    except AssertionError:
        logger.error("Null value of %s in job metadata, corrupt data?",n)
        return False

    metadata = dict.copy(raw_metadata)
    # Augment metadata where needed

    # job_pl_username will ALWAYS be present in new data, but
    # we have older data, so we retain the clause below:
    if not('job_pl_username' in metadata):
        username = get_batch_envvar("JOB_USER",raw_metadata['job_pl_env']) or get_batch_envvar("USER",raw_metadata['job_pl_env'])
        if username is False or len(username) < 1:
            logger.error("No job username found in environment")
            return False
        metadata['job_pl_username'] = username

    if not ('job_jobname' in metadata):
        jobname = get_batch_envvar("JOB_NAME",raw_metadata['job_pl_env'])
        if jobname is False or len(jobname) < 1:
            jobname = "unknown"
            logger.warning("No job name found found in environment, defaulting to %s",jobname)
        metadata['job_jobname'] = jobname

    if not ('job_tags' in metadata):
        # Look up job tags from stop environment
        job_tags = tag_from_string(raw_metadata['job_el_env'].get(settings.job_tags_env))
        logger.debug("job_tags: %s",str(job_tags))
        metadata['job_tags'] = job_tags

    if not ('job_env_changes' in metadata):
        # Compute difference in start vs stop environment
        # we can ignore all the fields returned except the first
        env_changes = get_metadata_env_changes(raw_metadata)[0]
        if env_changes:
            logger.debug('start/stop environment changed: {0}'.format(env_changes))
        metadata['job_env_changes'] = env_changes

    # mark the metadata as checked so we don't check it again unnecessarily
    metadata['checked'] = True
    return metadata

def check_pid(pid):
    """Check whether pid exists"""
    if pid < 0:
        return (False, 'Invalid PID: {0}'.format(pid))
    from os import kill
    try:
        kill(pid, 0)
    except OSError as err:
        from errno import ESRCH, EPERM
        if err.errno == ESRCH:
            # ESRCH == No such process
            return (False, 'No such process (PID: {0})'.format(pid))
        elif err.errno == EPERM:
            # EPERM clearly means there's a process but we cannot
            # send a signal to it
            return (True, 'Not authorized to send signals to it (EPERM)')
        else:
            # According to "man 2 kill" possible error values are
            # (EINVAL, EPERM, ESRCH)
            return (True, str(err.errno))
    return (True,'')

def suggested_cpu_count_for_submit():
    '''
    Suggests the optimal number of cpus to use for the submit operation
    '''
    return 1
    # from multiprocessing import cpu_count
    # max_procs = cpu_count()
    # return max(1, max_procs - 1)


def conv_to_datetime(t):
    """
    This converts a time specified as a string or a Unix timestamp
    or a negative integer (signifiying a relative offset in days
    from the current time) to a python datetime object. If passed a
    datetime object it will be returned without modification
    E.g., of valid values of t:

                '08/13/2019 23:29' (string)
                 1565606303 (Unix timestamp)
                 datetime.datetime(2019, 8, 13, 23, 29) (datetime object)
                 -1 => 1 day ago
                 -30 => 30 days ago
                 0 => now

    """
    from datetime import datetime, timedelta
    retval = t

    if type(t) == str:
        if not t: return None
        try:
            retval = datetime.strptime(t, '%m/%d/%Y %H:%M')
        except Exception as e:
            logger = getLogger(__name__)
            logger.error('could not convert string to datetime: %s' % str(e))
            return None
    elif type(t) in (int, float):
        if t > 0:
            retval = datetime.fromtimestamp((int)(t))
        else:
            # interpret a negative integer as number of days before now()
            # if it's zero interpret it as now
            retval = datetime.now() - timedelta(days=(-t))
    return retval


def ranges(i):
    """
    Return a list of ranges for a list of integers

    >>> print(list(ranges([0, 1, 2, 3, 4, 7, 8, 9, 11])))
    >>> [(0, 4), (7, 9), (11, 11)]
    """

    from itertools import groupby
    for a, b in groupby(enumerate(i), lambda pair: pair[1] - pair[0]):
        b = list(b)
        yield b[0][1], b[-1][1]

def atoi(text):
    return int(text) if text.isdigit() else text

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)

    >>> alist = [ 'phil10', 'phil1', 'phil11', 'phil0' ]
    >>> sorted(alist, key=natural_keys)
    ['phil0', 'phil1', 'phil10', 'phil11']
    '''
    import re
    return [ atoi(c) for c in re.split(r'(\d+)', text) ]


def hash_strings(v):
    '''
    Hashes a vector of strings and returns a vector of integers
    '''
    import hashlib
    x = [ dumps(s, sort_keys=True) if (type(s) != str) else s  for s in v ]
    return [ int(hashlib.sha256((s).encode('utf-8')).hexdigest(), 16) % 10**8 for s in x ]


def encode2ints(v):
    '''
    Encodes a vector of strings to a vector of ints
    https://stackoverflow.com/questions/53420705/python-reversibly-encode-alphanumeric-string-to-integer
    '''
    def encode_to_int(s):
        '''
        Encodes a string as an int
        '''
        if type(s) != str:
            s = dumps(s, sort_keys=True)
        mBytes = s.encode("utf-8")
        return int.from_bytes(mBytes, byteorder="little")
    return [ encode_to_int(s) for s in v ]

def decode2strings(v):
    '''
    Decodes a vector of ints to a vector of strings.
    The vector of ints MUST have been encoded using
    "encode_strings"
    '''
    def decode_string_from_int(n):
        '''
        Decodes a string from an int. The int MUST have
        been encoded using encode_string_to_int
        '''
        n = int(n) # in case n is an int64
        mBytes = n.to_bytes(((n.bit_length() + 7) // 8), byteorder="little")
        return mBytes.decode("utf-8")
    return [ decode_string_from_int(n) for n in v ]

def dframe_encode_features(df, features = [], reversible = False):
    '''
    Replaces feature columns containing string/object (non-numeric)
    values with columns containing encoded integers.

         df: Input dataframe possibly containing non-numeric feature columns

   features: If supplied, only these columns will be assumed to have
             non-numeric values, and hence only these columns will be
             mapped.

 reversible: If set, a reversible encoding is done so that the integer
             columns can be converted to the original strings if needed.
             It is not recommended that you enable this option as the
             resultant integers can be inordinately long for long strings

    RETURNS: (encoded_df, mapped_features)

         encoded_df: Output dataframe which contains non-numeric
                     feature columns replaced with encoded integer features.
   encoded_features: List of feature column names that were replaced with
                     encoded integers.

    NOTE: If encoded_features is empty, no features were encoded.
    '''
    logger = getLogger(__name__)
    if not features:
        import epmt.epmt_settings as settings
        logger.debug('Selecting non-numeric columns from dataframe and then pruning out blacklisted features')
        obj_features = list(df.select_dtypes(include='object').columns.values)
        logger.debug('Non-numeric features in dataframe: {}'.format(obj_features))
        logger.debug('Blacklisted features to prune: {}'.format(settings.outlier_features_blacklist))
        features = list(set(df.select_dtypes(include='object').columns.values) - set(settings.outlier_features_blacklist))

    if not features:
        logger.warning('No non-numeric, eligible, feature columns found in the dataframe; none encoded')
        return (df, [])

    if reversible:
        logger.warning('You have enabled "reversible". Be warned that the encoded feature columns can contain some very large integers')
    encoded_df = df.copy()
    encoded_features = []
    logger.debug('encoding feature columns: {}'.format(features))
    for c in features:
        str_vec = df[c].to_numpy()
        int_vec = encode2ints(str_vec) if reversible else hash_strings(str_vec)
        encoded_df[c] = int_vec
        logger.debug('mapped feature {}: {} -> {}'.format(c, str_vec, int_vec))
        encoded_features.append(c)
    logger.info('Encoded features: {}'.format(encoded_features))
    return (encoded_df, encoded_features)


def dframe_decode_features(df, features):
    '''
    Decodes features in dataframe that were previously encoded
    using dframe_encode_features(..., reversible=True)

           df: Input dataframe containing one or more feature columns
               that were encoded using dframe_encode_features

     features: List of feature names that need to be decoded

      RETURNS: (decoded_df, decoded_features)

               decoded_df: Dataframe with decoded features
         decoded_features: List of features that were decoded

        NOTE: Please check restored_features to ensure that the features
              were indeed decoded. Ensure reversible is set True, when
              calling dframe_encode_features, as otherwise the strings
              are hashed and not encoded (hashed strings cannot be decoded).
    '''
    logger = getLogger(__name__)
    decoded_df = df.copy()
    decoded_features = []
    for c in features:
        int_vec = df[c].to_numpy()
        str_vec = decode2strings(int_vec)
        decoded_df[c] = str_vec
        logger.debug('decoded {}: {} -> {}'.format(c, int_vec, str_vec))
        decoded_features.append(c)
    if decoded_features != features:
        logger.warning('decoded features list is not identical to requested features')
    if not decoded_features:
        logger.warning('No features were decoded')
    else:
        logger.info('Decoded features: {}'.format(decoded_features))
    return (decoded_df, decoded_features)


def find_files_in_dir(path, pattern = '*.tgz', recursive = False):
    '''
    Find files matching a pattern under a directory.

       path: Top-level directory to scan
    pattern: glob pattern to match. Defaults to '*.tgz'
  recursive: Scan recursively down or not

    RETURNS: List of files that match
    '''
    from glob import glob
    pathname = '{}/{}{}'.format(path, '**/' if recursive else '', pattern)
    return glob(pathname, recursive=recursive)

# https://www.python.org/dev/peps/pep-0257/
def docs_trim(docstring):
    '''
    Formats a docstring
    '''
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    LARGE_NUMBER = 10000 # just a large number
    indent = LARGE_NUMBER
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < LARGE_NUMBER:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)

def docs_func_summary(func):
    '''
    Returns the docstring summary for a function
    '''
    summary_string = ((func.__doc__ or '').lstrip().split('\n')[0].strip())
    # the summary string may have a section name at the end of it
    # separated by ::
    # So, if we have a :: in the string, then we split and take the first portion
    # as the actual summary
    return summary_string.rsplit('::', 1)[0] if '::' in summary_string else summary_string

def docs_func_section(func):
    '''
    Returns the section name (if any) for a function from its docstrings

    We assume a doctstring summary line has a double-colon followed by
    a section name at the end of the summary line.
    '''
    summary_string = ((func.__doc__ or '').lstrip().split('\n')[0].strip())
    return summary_string.rsplit('::', 1)[1] if '::' in summary_string else ''


def docs_module_index(mod, fmt=None):
    '''
    Returns a sorted list of functions and their summaries for a module

    Parameters
    ----------
        mod: python module
        fmt: Format of output. Present an unset or empty fmt means
             return a list of tuples. fmt == 'string' means returns
             a string.

    Returns
    -------
       A list of the form:
           [ (func1, summary1), (func2, summary2) ... ]

       where func1, func2,... are function names from the module
       sorted alphabetically or according to some other criteria
       such as category to which the function.

    '''
    from inspect import getmembers, isfunction

    # get sorted list of functions from the module "mod"
    # We skip functions whose names start with underscore (_)
    # and also functions that are not actually defined in the module, but
    # merely imported from some other module
    funcs = sorted( [
        o[1] for o in getmembers(mod) if isfunction(o[1]) and (not o[1].__name__.startswith('_')) and (o[1].__module__ == mod.__name__)], key = lambda f: f.__name__)

    # prepare a list of tuples; the first tuple number is the
    # function name, and the second item is it's one-line summary extracted
    # from it's docstring. Some functions may have no docstrings, and thats OK
    out = [ (f.__name__, docs_func_summary(f), docs_func_section(f)) for f in funcs ]
    if fmt != 'string':
        # return the list of tuples
        return out

    sections = {}
    for (name, summary, section) in out:
        section = section or 'Uncategorized'
        if section in sections:
            sections[section].append((name, summary))
        else:
            sections[section] = [(name, summary)]

    # user wants a human-readable string
    # get the maximum length of function names
    max_func_name_len = max([len(f.__name__) for f in funcs ])

    # format so we print the function name followed by the summary
    # with the correct spacing
    fmt_string = "{:" + str(max_func_name_len) + "s}    {}"
    out_str = ""
    for section in sorted(sections.keys()):
        section_calls = sections[section]
        out_str += "\n\nSection::{}\n".format(section)
        out_str += "\n".join([fmt_string.format(o[0], o[1]) for o in section_calls])
    return out_str

def get_install_root():
    '''
    Returns the install root. This function is specifically written
    to avoid os path functions so it can work under pyinstaller's
    hacked environment. It uses rsplit:

    >>> '/abc/def/ghi.py'.rsplit('/',1)
    ['/abc/def', 'ghi.py']
    '''
    #logger = getLogger(__name__)
    install_root = (__file__.rsplit('/', 2)[0])
    # handle pip packaging here -- even when "manually" installed ala 4.9.6, our install_dir should always end in /epmt.
    # XXX THIS IS STILL HOKEY and i'm not sure how to make it work for all possible installations.
    if not install_root.endswith('/epmt'):
        #logger.warning('WARNING: install_root = {}'.format(install_root) )
        #logger.warning('WARNING: install_root does not end with \"/epmt\"...')
        #logger.warning('WARNING: adding it to the install root...')
        install_root = install_root + '/epmt'
        #logger.warning('WARNING: install_root changed to {}'.format(install_root))
    #logger.debug('install root is {}'.format(install_root) )
    return install_root

def logfn(func):
    '''
    Logs function name and arguments
    '''
    @wraps(func)
    def log_func(*func_args, **func_kwargs):
        #print("HELLO from epmtlib.logfn")
        # get the module name from the function itself
        logger = getLogger(func.__module__)
        # we want to log a message like:
        #  FUNC_NAME(arg1, arg2..., kwarg1=xyz, kwarg2=abc, ...)
        # the module is prepended automatically by our logging format
        # as we use getLogger with the module name
        #logger.info('{}({}{}{})'.format(func.__name__,
        logger.debug('{}({}{}{})'.format(func.__name__,
                                         ", ".join( [ str(x) for x in func_args] ),
                                         "," if func_kwargs else "",
                                         ",".join( ["{}={}".format(k, v) for (k,v) in func_kwargs.items()] ) ))
        # now call the actual function with its arguments (if any)
        return func(*func_args, **func_kwargs)
    return log_func

def csv_probe_format(f):
    '''
    Returns the CSV file format and header

    Parameters
    ----------
            f : file handle or string
                If `f` is a file handle, it must be positioned at
                the beginning of the file

    Returns
    -------
    (version, header)
     version : string
               '1' or '2'
      header : list
               list of header columns (in-order)

    Notes
    -----
    EPMT supports two file formats '1' and '2'
    '1' is a comma-separated file, while '2' is a tab
    separated file. If the file does not have either
    of the above formats, we will raise an exception
    '''
    # handle the case where somebody gave us a file name
    close_file = False

    if type(f) == str:
        close_file = True
        f = open(f)
    # read the first few characters and check for the delimiter
    s = "".join([chr(x) for x in f.read(1024)])
    if close_file:
        f.close()
    else:
        f.seek(0) # restore file position to beginning of file
    if '\t' in s:
        # the second element is a list of CSV column names
        return ('2', s.split('\n')[0].split('\t'))
    elif ',' in s:
        # the second element is a list of CSV column names
        return ('1', s.split('\n')[0].split(','))
    # if we reached here, then we don't understand the CSV format
    raise ValueError("CSV file -- {} -- has an unknown file format. Is it corrupted?".format(f.name))

# Set up signal handlers. If no signals are specified, sensible
# defaults are used. If no handler is specified, the default
# handler is assumed (this means the signal handler will be restored
# to the default)
def set_signal_handlers(signals = [], handler = None):
    from signal import SIGHUP, SIGTERM, SIGINT, signal, SIG_DFL
    logger = getLogger(__name__)

    # set defaults
    signals = signals or [SIGHUP, SIGTERM, SIGINT]
    handler = handler or SIG_DFL

    for sig in signals:
        signal(sig, handler)
    if handler == SIG_DFL:
        logger.debug('Finished restoring signal handlers to defaults')
    else:
        logger.debug('Finished setting up signal handlers')


if __name__ == "__main__":
    print(version_str(True))
