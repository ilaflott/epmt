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
