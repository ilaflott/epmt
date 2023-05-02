from __future__ import print_function


def epmt_retire():
    #print(f'(epmt_cmd_retire.py: epmt_retire())------------FUNCTION CALL/STEP2')
    #print(f'no args.')
    import epmt.epmt_settings as settings
    from epmt.epmt_query import retire_jobs, retire_refmodels
    from logging import getLogger

    logger = getLogger(__name__)  # you can use other name
    num_jobs_retired = -1
    num_models_retired = -1

    import tracemalloc as tm













    #tm.start(25)
    tm.start()
    snapshot_print_top_N=20
    print_count=0

    
    ### ------- refmodels
    logger.info('Retiring models older than %d days', settings.retire_models_ndays)
    #print(f'(epmt_retire) retire_refmodels({settings.retire_models_ndays})')
    num_models_retired = retire_refmodels(settings.retire_models_ndays)
    #print(f'(epmt_retire) num_models_retired={num_models_retired}')
    
    retire_mods_snapshot=tm.take_snapshot()
    retire_mods_snapshot.dump('epmt_retire_refmodels_snapshot.txt')
    #print(f'tracemalloc.take_snapshot(): \n {retire_mods_snapshot}')
    
    print_count=0
    mods_lineno_snapshot_stats=retire_mods_snapshot.statistics('lineno')
    f_lineno_retire_mods_out=open('lineno_epmt_retire_mods_out.txt','w')    
    print(f'\n tracemalloc.take_snapshot().statistics(\'lineno\'): ')
    for stat in mods_lineno_snapshot_stats:
        print_count=print_count+1
        f_lineno_retire_mods_out.write(str(stat)+'\n')
        if print_count >= snapshot_print_top_N:
            continue
        #print(f'{stat}')
    f_lineno_retire_mods_out.close()
    

    #    ### ------- jobs
    #    logger.info('Retiring jobs older than %d days', settings.retire_jobs_ndays)
    #    #print(f'(epmt_retire) retire_jobs({settings.retire_jobs_ndays})')
    #    num_jobs_retired = retire_jobs(settings.retire_jobs_ndays)
    #    #print(f'(epmt_retire) num_jobs_retired={num_models_retired}')
    #    
    #    retire_jobs_snapshot=tm.take_snapshot()
    #    #retire_jobs_snapshot.dump('epmt_retire_jobs_snapshot.txt')
    #    #print(f'tracemalloc.take_snapshot(): \n {retire_jobs_snapshot}')
    #    
    #    print_count=0
    #    jobs_lineno_snapshot_stats=retire_jobs_snapshot.statistics('lineno')
    #    f_lineno_retire_jobs_out=open('lineno_epmt_retire_jobs_out.txt','w')    
    #    print(f'\n tracemalloc.take_snapshot().statistics(\'lineno\'): ')
    #    for stat in jobs_lineno_snapshot_stats:
    #        print_count=print_count+1
    #        f_lineno_retire_jobs_out.write(str(stat)+'\n')
    #        if print_count >= snapshot_print_top_N:
    #            continue
    #        #print(f'{stat}')
    #    f_lineno_retire_jobs_out.close()
    

    logger.info('%d jobs retired, %d models retired',num_jobs_retired, num_models_retired)

    print(f'\n(epmt_cmd_retire.py: epmt_retire())------------RETURNING (num_jobs_retired={num_jobs_retired}, num_models_retired={num_models_retired})')
    return (num_jobs_retired, num_models_retired)
