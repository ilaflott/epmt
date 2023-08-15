from __future__ import print_function

def epmt_retire(skip_unprocessed = False, dry_run = False):

    import epmt.epmt_settings as settings
    from epmt.epmt_query import retire_jobs, retire_refmodels
    from logging import getLogger
    logger = getLogger(__name__)
    
    num_models_retired = 0
    logger.info('Retiring models older than %d days', settings.retire_models_ndays)
    num_models_retired = retire_refmodels(settings.retire_models_ndays, dry_run=dry_run)

    import tracemalloc as tm
    tm.start()

    #__________________
    model_retire_size, model_retire_peak=tm.get_traced_memory()
    print(f'after model retire: memory_size={model_retire_size/1024/1000} MiB, memory_peak={model_retire_peak/1024/1000} MiB')
    tm.reset_peak()
    #------------------

    num_jobs_retired = 0
    logger.info('Retiring jobs older than %d days', settings.retire_jobs_ndays)
    num_jobs_retired = retire_jobs(settings.retire_jobs_ndays, skip_unprocessed = skip_unprocessed, dry_run=dry_run)

    #__________________
    job_retire_size, job_retire_peak=tm.get_traced_memory()
    print(f'  after job retire: memory_size={job_retire_size/1024/1000} MiB, memory_peak={job_retire_peak/1024/1000} MiB')
    tm.reset_peak()    
    #------------------

    logger.info('%d jobs retired, %d models retired',num_jobs_retired, num_models_retired)
    if dry_run:
        print(f'(dry_run=True) {num_jobs_retired} jobs and {num_models_retired} models will be retired')
    return (num_jobs_retired, num_models_retired)
