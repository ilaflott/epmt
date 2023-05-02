from __future__ import print_function

def epmt_retire():
    import epmt.epmt_settings as settings
    from epmt.epmt_query import retire_jobs, retire_refmodels
    from logging import getLogger
    logger = getLogger(__name__)  # you can use other name
    num_jobs_retired = 0
    num_models_retired = 0

    #import tracemalloc as tm
    #tm.start()
    
    ### ------- refmodels
    logger.info('Retiring models older than %d days', settings.retire_models_ndays)
    num_models_retired = retire_refmodels(settings.retire_models_ndays)
    
    #retire_mods_snapshot=tm.take_snapshot()    
    #f_lineno_retire_mods_out=open('lineno_epmt_retire_mods_out.txt','w')    
    #mods_lineno_snapshot_stats=retire_mods_snapshot.statistics('lineno')
    #for stat in mods_lineno_snapshot_stats:
    #    f_lineno_retire_mods_out.write(str(stat)+'\n')
    #f_lineno_retire_mods_out.close()
    

    ### ------- jobs
    logger.info('Retiring jobs older than %d days', settings.retire_jobs_ndays)
    num_jobs_retired = retire_jobs(settings.retire_jobs_ndays)
    
    #retire_jobs_snapshot=tm.take_snapshot()    
    #f_lineno_retire_jobs_out=open('lineno_epmt_retire_jobs_out.txt','w')    
    #jobs_lineno_snapshot_stats=retire_jobs_snapshot.statistics('lineno')
    #for stat in jobs_lineno_snapshot_stats:
    #    f_lineno_retire_jobs_out.write(str(stat)+'\n')
    #f_lineno_retire_jobs_out.close()    

    logger.info('%d jobs retired, %d models retired',num_jobs_retired, num_models_retired)

    print(f'\n(epmt_cmd_retire.py: epmt_retire())------------RETURNING (num_jobs_retired={num_jobs_retired}, num_models_retired={num_models_retired})')
    return (num_jobs_retired, num_models_retired)
