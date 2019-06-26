from __future__ import print_function
from functools import wraps
from time import time

def timing(f):
    @wraps(f)
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        print('%r took: %2.4f sec' % (f.__name__, te-ts))
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
