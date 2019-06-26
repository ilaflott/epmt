from functools import wraps
from time import time
from sys import stdout
from logging import getLogger, basicConfig, DEBUG, ERROR, INFO, WARNING
from os import environ

# if check is set, then we will bail if logging has already been initialized
def set_logging(intlvl = 0, check = False):
    if check and hasattr(set_logging, 'initialized'):
        return
    set_logging.initialized = True
    if intlvl < 0:
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
    for k in [ "provider", "user", "password", "host", "dbname", "filename" ]:
        name = "EPMT_DB_"+ k.upper()
        t = environ.get(name)
        if t:
            logger.info("%s found, setting %s:%s now %s:%s",name,k,settings.db_params[k],k,t)
            settings.db_params[k] = t

    if not hasattr(settings, 'job_tags_env'):
        logger.warning("missing settings.job_tags_env")
        settings.job_tags_env = 'EPMT_JOB_TAGS'
    if not hasattr(settings, 'jobid_env_list'):
        logger.warning("missing settings.jobid_env_list")
        settings.jobid_env_list = [ "SLURM_JOB_ID", "SLURM_JOBID", "PBS_JOB_ID" ]
    if not hasattr(settings, 'verbose'):
        logger.warning("missing settings.verbose")
        settings.verbose = 0
    if not hasattr(settings, 'stage_command'):
        logger.warning("missing settings.stage_command ")
        settings.stage_command = "cp"
    if not hasattr(settings, 'stage_command_dest'):
        logger.warning("missing settings.stage_command_dest")
        settings.stage_command_dest = "."
    if not hasattr(settings, 'allow_job_deletion'):
        logger.warning("missing settings.allow_job_deletion")
        settings.allow_job_deletion = False
    if not hasattr(settings, 'per_process_fields'):
        logger.warning("missing settings.per_process_fields")
        settings.per_process_fields = ["tags","hostname","exename","path","args","exitcode","pid","generation","ppid","pgid","sid","numtids"]
    if not hasattr(settings, 'skip_for_thread_sums'):
        logger.warning("missing settings.skip_for_thread_sums")
        settings.skip_for_thread_sums = ["tid", "start", "end", "num_threads", "starttime"]
    if not hasattr(settings, 'all_tags_field'):
        logger.warning("missing settings.all_tags_field")
        settings.all_tags_field = 'all_proc_tags'

def timing(f):
    @wraps(f)
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        stdout.write('%r took: %2.4f sec\n' % (f.__name__, te-ts))
        return result
    return wrap

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
    if not s or len(s) == 0:
        return None
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
    if type(tags) == str:
        tags = [tag_from_string(tags)]
    elif type(tags) == dict:
        tags = [tags]
    tags = [tag_from_string(t) if type(t)==str else t for t in tags]
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

# return the sum of keys across two dictionaries
# x = {'both1':1, 'both2':2, 'only_x': 100 }
# y = {'both1':10, 'both2': 20, 'only_y':200 }
# {'only_y': 200, 'both2': 22, 'both1': 11, 'only_x': 100}
def sum_dicts(x, y):
    return { k: x.get(k, 0) + y.get(k, 0) for k in set(x) | set(y) }

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
    from numpy import unique, array
    return unique(array(new_dicts)).tolist()

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


