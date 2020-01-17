from functools import wraps
from time import time
from logging import getLogger, basicConfig, DEBUG, ERROR, INFO, WARNING, CRITICAL
from os import environ, unlink, devnull, getuid
from contextlib import contextmanager
from subprocess import call
from json import dumps, loads
from pwd import getpwuid

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

# semantic version
# first element is the major version number
# second element is the minor version number
# third element is the patch or bugfix number
# Since we are saving as a tuple you can do a simple
# compare of two version tuples and python will do the right thing
_version = (3,1,2)

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
    import epmt_settings as settings

    if check and hasattr(epmt_logging_init, 'initialized'): return
    epmt_logging_init.initialized = True
    if intlvl == None:
        intlvl = 0
    intlvl = int(intlvl)
    if intlvl < -1:
        level = CRITICAL
    if intlvl == -1:
        level = ERROR
    if intlvl == 0:
        level = WARNING
    if intlvl == 1:
        level = INFO
    elif intlvl >= 2:
        level = DEBUG

    rootLogger = getLogger()
    rootLogger.setLevel(level)
    # basicConfig(filename='epmt.log', filemode='a', level=level)
    logFormatter = logging.Formatter("[%(asctime)-19.19s, %(process)6d] %(levelname)-7.7s %(name)s:%(message)s")
    fileHandler = logging.FileHandler(settings.logfile)
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler()
    consoleFormatter = logging.Formatter("[PID %(process)d] %(levelname)7.7s: %(name)s: %(message)s" if log_pid else "%(levelname)7.7s: %(name)s: %(message)s")
    consoleHandler.setFormatter(consoleFormatter)
    rootLogger.addHandler(consoleHandler)

    for handler in rootLogger.handlers:
        handler.setLevel(level)

    # matplotlib generates a ton of debug messages
    mpl_logger = logging.getLogger('matplotlib') 
    mpl_logger.setLevel(logging.WARNING) 


def init_settings(settings):
    logger = getLogger(__name__)
    err_msg = ""

    if environ.get("PAPIEX_OUTPUT"):
        logger.warning("PAPIEX_OUTPUT variable should not be defined, it will be ignored")
    if environ.get("PAPIEX_OPTIONS"):
        logger.warning("PAPIEX_OPTIONS variable should not be defined, it will be ignored")

    for k in [ "provider", "user", "password", "host", "dbname", "filename" ]:
        name = "EPMT_DB_"+ k.upper()
        t = environ.get(name)
        if t:
            logger.info("%s found, setting %s:%s now %s:%s",name,k,settings.db_params[k],k,t)
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
        settings.stage_command_dest = "."
    if not hasattr(settings, 'input_pattern'):
        logger.warning("missing settings.input_pattern")
        settings.input_pattern = "*-papiex-*-[0-9]*.csv"
    if not hasattr(settings, 'per_process_fields'):
        logger.warning("missing settings.per_process_fields")
        settings.per_process_fields = ["tags","hostname","exename","path","args","exitcode","pid","generation","ppid","pgid","sid","numtids"]
    if not hasattr(settings, 'skip_for_thread_sums'):
        logger.warning("missing settings.skip_for_thread_sums")
        settings.skip_for_thread_sums = ["tid", "start", "end", "num_threads", "starttime"]
    if not hasattr(settings, 'all_tags_field'):
        logger.warning("missing settings.all_tags_field")
        settings.all_tags_field = 'all_proc_tags'
    if not hasattr(settings, 'outlier_thresholds'):
        logger.warning("missing settings.outlier_thresholds")
        settings.outlier_thresholds = { 'modified_z_score': 2.5, 'iqr': [20,80], 'z_score': 3.0 }
    if not hasattr(settings, 'outlier_features'):
        logger.warning("missing settings.outlier_features")
        settings.outlier_features = ['duration', 'cpu_time', 'num_procs']
    if not hasattr(settings, 'outlier_features_blacklist'):
        logger.warning("missing settings.outlier_features_blacklist")
        settings.outlier_features_blacklist = []
    if not hasattr(settings, 'bulk_insert'):
        logger.warning("missing settings.bulk_insert")
        settings.bulk_insert = False
    if (settings.orm != 'sqlalchemy' and settings.bulk_insert):
        err_msg += '\n - bulk_insert is only supported by sqlalchemy'
    if not hasattr(settings, 'post_process_job_on_ingest'):
        logger.warning("missing settings.post_process_job_on_ingest")
        settings.post_process_job_on_ingest = True
    if not hasattr(settings, 'lazy_compute_process_tree'):
        logger.warning("missing settings.lazy_compute_process_tree")
        settings.lazy_compute_process_tree = True
    if ((settings.orm != 'sqlalchemy') and (not(settings.post_process_job_on_ingest))):
        err_msg += '\n - post_process_job_on_ingest set as False is only permitted with sqlalchemy'
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
    # rc = run_shell_cmd('which', cmd)
    # return (rc == 0)
    from shutil import which
    return which(cmd) is not None

def safe_rm(f):
    if not(f): return False
    try:
        unlink(f)
        return True
    except Exception as e:
        pass
    return False

def timing(f):
    logger = getLogger(__name__)
    @wraps(f)
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        logger.info('%r took: %2.5f sec' % (f.__name__, te-ts))
        return result
    return wrap



@contextmanager
def capture():
    import sys
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err

# we assume tag is of the format:
#  "key1:value1 ; key2:value2"
# where the whitespace is optional and discarded. The output would be:
# { "key1": value1, "key2": value2 }
#
# We can also handle the case where a value is not set for
# a key, by assigning a default value for the key
# For example, for the input:
# "multitheaded;app=fft" and a tag_default_value="1"
# the output would be:
# { "multithreaded": "1", "app": "fft" }
#
# Note, both key and values will be strings and no attempt will be made to
# guess the type for integer/floats
def tag_from_string(s, delim = ';', sep = ':', tag_default_value = '1'):
    from pony.orm.ormtypes import TrackedDict
    if type(s) in (dict, TrackedDict): return s
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

# returns a list of tags, where each tag is a dict.
# the input can be a list of strings or a single string.
# each string will be converted to a dict
def tags_list(tags):
    from pony.orm.ormtypes import TrackedDict
    # do we have a single tag in string or dict form? 
    if isString(tags):
        tags = [tag_from_string(tags)]
    elif type(tags) in [dict, TrackedDict]:
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

# return the sum of keys across two dictionaries
# x = {'both1':1, 'both2':2, 'only_x': 100 }
# y = {'both1':10, 'both2': 20, 'only_y':200 }
# {'only_y': 200, 'both2': 22, 'both1': 11, 'only_x': 100}
def sum_dicts(x, y):
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
def kwargify(list_of_str):
    myDict = {}
    jobs = []
    for s in list_of_str:
        if not "=" in s:
            jobs.append(s)
        else:
            a, b = s.split('=')
            if check_int(b):
                myDict[a] = int(b)
            elif check_boolean(b):
                myDict[a] = bool(b)
            elif check_none(b):
                myDict[a] = None
            else: #string
                myDict[a] = b
    if myDict.get('jobs') == None and jobs:
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

    import epmt_settings as settings
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
            print(raw_metadata['job_pl_env'])
            logger.error("No job username found in metadata or environment")
            return False
        metadata['job_pl_username'] = username

    if not ('job_jobname' in metadata):
        jobname = get_batch_envvar("JOB_NAME",raw_metadata['job_pl_env'])
        if jobname is False or len(jobname) < 1:
            jobname = "unknown"
            logger.warning("No job name found, defaulting to %s",jobname)
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
    from multiprocessing import cpu_count
    max_procs = cpu_count()
    return max(1, max_procs - 1)

if __name__ == "__main__":
    print(version_str(True))
