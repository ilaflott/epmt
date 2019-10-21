import sys
from functools import wraps
from time import time
from logging import getLogger, basicConfig, DEBUG, ERROR, INFO, WARNING, CRITICAL
from os import environ, unlink, devnull
from contextlib import contextmanager
from subprocess import call
from json import dumps, loads
from pony.orm.ormtypes import TrackedDict

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

# if check is set, then we will bail if logging has already been initialized
def set_logging(intlvl = 0, check = False):
    if check and hasattr(set_logging, 'initialized'): return
    set_logging.initialized = True
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
    basicConfig(level=level)
    logger = getLogger()
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)

def init_settings(settings):
    logger = getLogger(__name__)

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
        logger.error("missing settings.epmt_output_prefix")
        exit(1)
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
    if not hasattr(settings, 'bulk_insert'):
        logger.warning("missing settings.bulk_insert")
        settings.bulk_insert = False
    if (settings.orm != 'sqlalchemy' and settings.bulk_insert):
        logger.error('bulk_insert is only supported by sqlalchemy')
        sys.exit(1)
    if not hasattr(settings, 'post_process_job_on_ingest'):
        logger.warning("missing settings.post_process_job_on_ingest")
        settings.post_process_job_on_ingest = True
    if ((settings.orm != 'sqlalchemy') and (not(settings.post_process_job_on_ingest))):
        logger.error('post_process_job_on_ingest set as False is only permitted with sqlalchemy')
        sys.exit(1)
    if not hasattr(settings, 'db_params'):
        logger.error("missing settings.db_params")
        sys.exit(1)

def run_shell_cmd(*cmd):
    nf = open(devnull, 'w')
    rc = call(cmd, stdout=nf, stderr=nf)
    return rc

def cmd_exists(cmd):
    if not cmd: return False
    rc = run_shell_cmd('which', cmd)
    return (rc == 0)

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
        logger.debug('%r function took: %2.4f sec\n' % (f.__name__, te-ts))
        return result
    return wrap



@contextmanager
def capture():
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
    if type(s) in (dict, TrackedDict): return s
    if not s: return (None if s == None else {})

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
