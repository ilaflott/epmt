from models import *
from epmt_job import setup_orm_db
import settings
print(settings.db_params)
setup_orm_db(settings)


THR_SUMS_FIELD = 'threads_sums'
# Filter a supplied set of Process objects to find a match
# by tags or some primary keys. If the process_set is not
# specified then the query will be run against all processes.
# 'tags' is a key/value pair and is optional.
# 'fltr' is a lambda expression or a string of the form:
#        lambda p: p.duration > 1000
#        OR
#        'p.duration > 1000 and p.numtids < 4'
# limit: if set, limits the total number of results
# 
# fmt :   Output format, is one of 'dict', 'orm', 'pandas'
#         'dict': This is the default, and in this case
#                 each process is output as a python dictionary, 
#                 and the entire output is a list of dictionaries.
#         'pandas': output is a pandas dataframe
#         'orm': output is a list of ORM objects
#
# merge_sum_fields: By default, this is True, and this means threads sums are
#          are folded into the process. If set to False, the threads'
#          sums will be available as a separate field THR_SUMS_FIELD.
#          Flattening makes subsequent processing easier as all the
#          thread aggregates such as 'usertime', 'systemtime' are available
#          as first-class members of the process. This option is silently
#          ignored if output format 'fmt' is set to 'orm', and ORM
#          objects will not be merge_sum_fieldsed.
#
# For example, to get all processes for a particular Job, with jobid '32046', which
# are multithreaded, you would do:
#
#   filter_processes(jobs = ['32046'], fltr = 'p.numtids > 1')
#
# To filter all processes that have tags = {'app': 'fft'}, you would do:
# filter_processes(tags = {'app': 'fft'})
#
# to get a pandas dataframe:
# qs1 = filter_processes(tags = {'app': 'fft'}, fmt = 'pandas')
#
# to filter processes for a job '1234' and order by process duration,
# getting the top 10 results, and keeping the final output in ORM format:
# 
# q = filter_processes(['1234'], order = 'desc(p.duration)', limit=10, fmt='orm')
#
# now, let's filter processes with duration > 100000 and order them by user+system time,
# and let's get the output into a pandas dataframe:
# q = filter_processes(fltr = (lambda p: p.duration > 100000), order = 'desc(p.threads_sums["user+system"]', fmt='pandas')
# Observe, that while 'user+system' is a metric available in the threads_sums field,
# by using the default merge_sum_fields=True, it will be available as column in the output
# dataframe. The output will be pre-sorted on this field because we have set 'order'
#
def filter_processes(jobs = [], tags = {}, fltr = None, order = '', limit = 0, fmt='dict', merge_sum_fields=True):
    if jobs:
        # is jobs a collection of Job IDs or actual Job objects?
        if type(jobs[0]) == str or type(jobs[0]) == unicode:
            # jobs is a list of job IDs
            qs = Process.select(lambda p: p.job.jobid in jobs)
        else:
            # jobs is a list of Job objects
            qs = Process.select(lambda p: p.job in jobs)
    else:
        # no jobs set, so expand the scope to all Process objects
        qs = Process.select()

    # filter using tags if set
    for (k,v) in tags.items():
        qs = qs.filter(lambda p: p.tags[k] == v)

    # if fltr is a lambda function or a string apply it
    if fltr:
        qs = qs.filter(fltr)

    if order:
        qs = qs.order_by(order)

    # finally set limits on the number of processes returned
    if limit:
        qs = qs.limit(int(limit))

    if fmt == 'orm':
        return qs[:]

    # convert the ORM into a list of dictionaries, excluding blacklisted fields
    proc_exclude_fields = settings.query_process_fields_exclude if hasattr(settings, 'query_process_fields_exclude') else []
    out_list = [ p.to_dict(exclude = proc_exclude_fields) for p in qs ]

    # do we need to merge threads' sum fields into the process?
    if merge_sum_fields:
        for p in out_list:
            p.update(p[THR_SUMS_FIELD])
        del p[THR_SUMS_FIELD]

    if fmt == 'pandas':
        from pandas import DataFrame
        return DataFrame(out_list)

    # we assume the user wants the output in the form of a list of dicts
    return out_list
