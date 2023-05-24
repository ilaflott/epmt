from __future__ import print_function

def epmt_retire(dry_run = False):

    import epmt.epmt_settings as settings
    from epmt.epmt_query import retire_jobs, retire_refmodels
    from logging import getLogger
    logger = getLogger(__name__)  # you can use other name
    num_jobs_retired = 0
    num_models_retired = 0

    logger.info('Retiring models older than %d days', settings.retire_models_ndays)
    num_models_retired = retire_refmodels(settings.retire_models_ndays, dry_run=dry_run)

    import tracemalloc as tm
    tm.start()

    #__________________
    print(f'second pos, current tracemalloc mem usage before recording snapshots, taking peak measurements...')
    print(f'{tm.get_tracemalloc_memory()/1024/1000} MiB')
    second_size, second_peak=tm.get_traced_memory()
    #tm.take_snapshot().dump('tm_snapshot2')
    print(f'after model retire: memory_size={second_size/1024/1000} MiB, memory_peak={second_peak/1024/1000} MiB')
    tm.reset_peak()
    #------------------

    logger.info('Retiring jobs older than %d days', settings.retire_jobs_ndays)
    num_jobs_retired = retire_jobs(settings.retire_jobs_ndays, dry_run=dry_run)

    #__________________
    print(f'third pos, current tracemalloc mem usage before recording snapshots, taking peak measurements...')
    print(f'{tm.get_tracemalloc_memory()/1024/1000} MiB')
    third_size, third_peak=tm.get_traced_memory()
    #tm.take_snapshot().dump('tm_snapshot3')
    print(f'  after job retire: memory_size={third_size/1024/1000} MiB, memory_peak={third_peak/1024/1000} MiB')
    tm.reset_peak()    
    #------------------

    logger.info('%d jobs retired, %d models retired',num_jobs_retired, num_models_retired)
    if dry_run:
        print(f'(dry_run=True) {num_jobs_retired} jobs and {num_models_retired} models will be retired')
    return (num_jobs_retired, num_models_retired)
