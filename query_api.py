from models import *
from epmt_job import setup_orm_db
import settings
print(settings.db_params)
setup_orm_db(settings)


PROC_EXCLUDE_FIELDS = ['threads_df']

# Filter a supplied set of Process objects to find a match
# by tags or some primary keys. If the process_set is not
# specified then the query will be run against all processes.
# 'tags' is a key/value pair and is optional.
# 'fltr' is a lambda expression or a string of the form:
#        lambda p: p.duration > 1000
#        OR
#        'p.duration > 1000 and p.numtids < 4'
# 'limit' if set, limits the total number of results
# 
# 'conv_orm_objects': This is true by default, and filter_processes
#        returns a list of matching processes that satisfy the
#        filters. All objects are converted to Python lists
#        or dictionaries. If set to False, then no conversions
#        will be performed. One reason to not convert ORM
#        objects would be if you want to use the objects
#        for chaining further queries. 
#
# example, to get all processes for a particular Job(j), which
# are multithreaded, you would do:
#
#   filter_processes(j.processes, fltr = 'p.numtids > 1')
#
# To filter all processes that have tags = {'app': 'fft'}, you would do:
# filter_processes(tags = {'app': 'fft'})
#
# And, if you want to chain filters, you can choose to not convert
# the returned ORM objects into Python lists/dictionaries:
# qs1 = filter_processes(tags = {'app': 'fft'}, conv_orm_objects = False)
# qs2 = filter_processes(qs1, tags = {'app': 'fft'})
#
def filter_processes(process_set = None, tags = {}, fltr = None, conv_orm_objects = True, limit = 0):
    qs = (process_set or Process).select()
    for (k,v) in tags.items():
        qs = qs.filter(lambda p: p.tags[k] == v)
    if fltr:
        qs = qs.filter(fltr)
    if limit:
        qs = qs.limit(int(limit))
    return [ p.to_dict(exclude = PROC_EXCLUDE_FIELDS) for p in qs ] if conv_orm_objects else qs
