from __future__ import print_function

def epmt_retire():
    import epmt.epmt_settings as settings
    from epmt.epmt_query import retire_jobs, retire_refmodels
    from logging import getLogger
    logger = getLogger(__name__)  # you can use other name
    num_jobs_retired = 0
    num_models_retired = 0

    logger.info('Retiring models older than %d days', settings.retire_models_ndays)
    num_models_retired = retire_refmodels(settings.retire_models_ndays)

    logger.info('Retiring jobs older than %d days', settings.retire_jobs_ndays)
    num_jobs_retired = retire_jobs(settings.retire_jobs_ndays)

    logger.info('%d jobs retired, %d models retired',num_jobs_retired, num_models_retired)
    return (num_jobs_retired, num_models_retired)
