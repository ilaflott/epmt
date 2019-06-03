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
# 'out_fmt': Output format, is one of 'dict', 'orm', 'pandas'
#            The default is 'dict', which case each process is
#            output as a python dictionary, and the output is 
#            a list of dictionaries.
#            'pandas': output is a pandas dataframe
#            'orm': output is a list of ORM objects
#
# example, to get all processes for a particular Job, with jobid '32046', which
# are multithreaded, you would do:
#
#   filter_processes(jobs = ['32046'], fltr = 'p.numtids > 1')
#
# To filter all processes that have tags = {'app': 'fft'}, you would do:
# filter_processes(tags = {'app': 'fft'})
#
# to get a pandas dataframe:
# qs1 = filter_processes(tags = {'app': 'fft'}, out_fmt = 'pandas')
#
def filter_processes(jobs = [], tags = {}, fltr = None, limit = 0, out_fmt='dict'):
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

    # finally set limits on the number of processes returned
    if limit:
        qs = qs.limit(int(limit))

    # return a list of processes, but first make sure we
    # convert each of the Process objects to a dictionary (excluding blacklisted
    # fields) unless conv_orm_objects is False
    proc_exclude_fields = settings.query_process_fields_exclude if hasattr(settings, 'query_process_fields_exclude') else []
    if out_fmt == 'orm': return qs[:]
    out_list = [ p.to_dict(exclude = proc_exclude_fields) for p in qs ]
    if out_fmt == 'pandas':
        from pandas import DataFrame
        return DataFrame(out_list)
    return out_list # just return a list of python dictionaries
