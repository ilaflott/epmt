"""
EPMT delete command module - handles job deletion functionality.
"""
from epmt.epmt_query import delete_jobs
from logging import getLogger
logger = getLogger(__name__)  # you can use other name


def epmt_delete_jobs(joblist):
    ''' Takes string
    Returns a boolean? if the list of successfully deleted jobid's as strings is as long as the delete_jobs return
    i.e. if there are jobs that were not deleted, return false. if all jobs were deleted successfully, return true.
    '''
    logger.debug("epmt_delete_jobs: %s", str(joblist))
    if not joblist or len(joblist) == 0:
        logger.error("joblist must not be empty")
        raise ValueError()

    # Delete jobs should return which ones don't get deleted if it cannot guarantee atomicity
    logger.info("deleted jobs %s", str(joblist))
    n_del_jobs = delete_jobs(joblist, force=True)
    if n_del_jobs != len(joblist):
        logger.warning("Warning! Some jobs could not be deleted.")
    return (delete_jobs(joblist, force=True) == len(joblist))
