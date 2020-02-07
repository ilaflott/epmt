from __future__ import print_function
import epmt_query as eq
from logging import getLogger

def epmt_show_job(jobid):
    logger = getLogger(__name__)  # you can use other name
    if type(jobid) == list:
        jobid = jobid[0]
    jobs = eq.get_jobs([jobid], fmt='dict')
    if len(jobs) != 1:
        logger.error('Job %s could not be found in database' % jobid)
        return False
    j_dict = jobs[0]
    for key in sorted(j_dict.keys()):
        # if attr.startswith('_'): continue
        # if attr in EXCLUDE_ATTR: continue
        # print("%-20s\t%-20s" % ( attr, getattr(j, attr)))
        print("%-20s      %-20s" % (key, j_dict[key]))
    return True
