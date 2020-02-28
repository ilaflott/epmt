from __future__ import print_function

def epmt_retire():
    import epmt_settings as settings
    from epmt_query import retire_jobs, retire_refmodels
    from logging import getLogger
    logger = getLogger(__name__)  # you can use other name
    num_jobs_retired = 0
    num_models_retired = 0
    # print('retire settings:', settings.retire_jobs_ndays, settings.retire_models_ndays)
    if settings.retire_models_ndays:
        logger.info('Retiring models older than %d days', settings.retire_models_ndays)
        num_models_retired = retire_refmodels(settings.retire_models_ndays)
    else:
        logger.debug("Not retiring any models (based on the data retention policy in settings.py)")
    if settings.retire_jobs_ndays:
        logger.info('Retiring jobs older than %d days', settings.retire_jobs_ndays)
        num_jobs_retired = retire_jobs(settings.retire_jobs_ndays)
    else:
        logger.debug("Not retiring any jobs (based on the data retention policy in settings.py)")
    print('\n{0} jobs retired\n{1} models retired'.format(num_jobs_retired, num_models_retired))
    return (num_jobs_retired, num_models_retired)
