from epmt_query import get_jobs
from logging import getLogger
from epmtlib import kwargify
#import pandas
logger = getLogger(__name__)  # you can use other name

def epmt_list_jobs(arglist):
    logger.info("epmt_list_jobs: %s",str(arglist))
    kwargs = kwargify(arglist)
    jobs = get_jobs(**kwargs)
#    if type(jobs) == pandas.core.frame.DataFrame:
    if len(jobs) == 0:
        logger.error("get_jobs %s failed\n",str(kwargs))
        return False
    print(jobs)
    return True

