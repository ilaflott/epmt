"""
EPMT show command module - handles job display functionality.
"""
# from __future__ import print_function
from logging import getLogger
import epmt.epmt_query as eq


def epmt_show_job(jobid, key=None):
    logger = getLogger(__name__)  # you can use other name
    if isinstance(jobid, list):
        jobid = jobid[0]
    jobs = eq.get_jobs([jobid], fmt='dict')
    if len(jobs) != 1:
        logger.error('Job %s could not be found in database' % jobid)
        return False
    j_dict = jobs[0]
    if key:
        if key in j_dict:
            print(j_dict[key])
        else:
            logger.error('Key "{}" was not found as an attribute of the job table'.format(key))
            print('Here are the keys that were found: {}'.format(",".join(sorted(j_dict.keys()))))
            return False
    else:
        for k in sorted(j_dict.keys()):
            print("%-20s      %-20s" % (k, j_dict[k]))
    return True
