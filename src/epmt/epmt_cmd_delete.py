from epmt.epmt_query import delete_jobs
from logging import getLogger
logger = getLogger(__name__)  # you can use other name

# Takes string
# Returns list of successfully deleted jobid's as strings

def epmt_delete_jobs(joblist):
    logger.info("epmt_delete_jobs: %s",str(joblist))
    if not joblist or len(joblist) == 0:
        logger.error("joblist must not be empty")
        return False
# Delete jobs should return which ones don't get deleted if it cannot
# guarantee atomicity
    if delete_jobs(joblist, force=True) != len(joblist):
        return False
    logger.info("deleted jobs %s",str(joblist))
    return True

