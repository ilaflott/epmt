"""
EPMT retire command module - handles retirement of jobs and models.
"""
from epmt.epmt_query import retire_jobs, retire_refmodels
from epmt.epmt_settings import retire_models_ndays, retire_jobs_ndays
import tracemalloc as tm
from logging import getLogger
logger = getLogger(__name__)


# import epmt.epmt_settings as settings


def epmt_retire(skip_unprocessed=False, dry_run=False):

    # start memory tracing during routine
    tm.start()

    logger.warning('Retiring models older than %d days', retire_models_ndays)
    num_models_retired = retire_refmodels(retire_models_ndays, dry_run=dry_run)

    # __________________
    model_retire_size, model_retire_peak = tm.get_traced_memory()
    logger.info(
        f'after model retire: memory_size={model_retire_size/1024/1000} MiB, memory_peak={model_retire_peak/1024/1000} MiB')
    tm.reset_peak()

    # ------------------
    logger.warning('Retiring jobs older than %d days', retire_jobs_ndays)
    num_jobs_retired = retire_jobs(retire_jobs_ndays, skip_unprocessed=skip_unprocessed, dry_run=dry_run)

    # __________________
    job_retire_size, job_retire_peak = tm.get_traced_memory()
    logger.info(
        f'  after job retire: memory_size={job_retire_size/1024/1000} MiB, memory_peak={job_retire_peak/1024/1000} MiB')
    tm.reset_peak()

    # ------------------
    logger.info('%d jobs retired, %d models retired', num_jobs_retired, num_models_retired)
    if dry_run:
        logger.info(f'(dry_run=True) {num_jobs_retired} jobs and {num_models_retired} models will be retired')

    # end memory tracing
    tm.stop()

    return (num_jobs_retired, num_models_retired)
