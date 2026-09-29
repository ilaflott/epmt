"""
EPMT dbcare module - executes tasks for taking care of the database, designed to be run on a regular basis
"""

import time
from logging import getLogger

from epmt.epmt_cmd_retire import epmt_retire
from epmt.epmt_query import post_process_jobs
from epmt.orm.sqlalchemy import orm_raw_sql
import epmt.orm.sqlalchemy.general as orm_general

logger = getLogger(__name__)

VACUUM_TABLES = ['processes_staging', 'processes', 'jobs']


def _get_dead_row_stats():
    """Query pg_stat_user_tables for live/dead row counts of vacuum target tables."""
    table_list = ", ".join(f"'{t}'" for t in VACUUM_TABLES)
    sql = (
        "SELECT relname, n_live_tup, n_dead_tup, last_vacuum, last_autovacuum "
        "FROM pg_stat_user_tables "
        f"WHERE relname IN ({table_list}) "
        "ORDER BY relname"
    )
    result = orm_raw_sql(sql)
    logger.debug('result = %s', result)
    #logger.debug('type(result) = %s', type(result))
    return result


def _vacuum_tables():
    """Run VACUUM VERBOSE on target tables using an autocommit connection.

    VACUUM cannot run inside a transaction, so we obtain a raw DBAPI
    connection and set it to autocommit mode.
    """
    engine = orm_general.engine
    if engine is None:
        logger.error('no database engine available, cannot vacuum')
        return

    # log dead row stats before vacuuming
    try:
        stats = _get_dead_row_stats()
        for row in stats:
            logger.info('pre-vacuum stats: table=%s live_rows=%s dead_rows=%s '
                        'last_vacuum=%s last_autovacuum=%s',
                        row[0], row[1], row[2], row[3], row[4])
    except Exception as e:
        logger.error('could not query dead row stats: %s', e)
        raise Exception from e


    # VACUUM requires autocommit — use a raw DBAPI connection
    raw_conn = engine.raw_connection()
    try:
        raw_conn.set_isolation_level(0)  # 0 = ISOLATION_LEVEL_AUTOCOMMIT
        cursor = raw_conn.cursor()

        # limit parallel maintenance workers for serial execution
        logger.info('setting max_parallel_maintenance_workers = 0 (serial execution)')
        cursor.execute('SET max_parallel_maintenance_workers = 0')

        for table in VACUUM_TABLES:
            logger.info('vacuuming table: %s', table)
            try:
                cursor.execute(f'VACUUM (VERBOSE) {table}')
                # VACUUM VERBOSE output comes through as NOTICEs;
                # fetch any notices from the connection
                if hasattr(raw_conn, 'notices') and raw_conn.notices:
                    for notice in raw_conn.notices:
                        logger.info('vacuum %s: %s', table, notice.strip())
                    raw_conn.notices.clear()
                logger.info('finished vacuuming table: %s', table)
            except Exception as e:
                logger.error('error vacuuming table %s: %s', table, e)
    finally:
        cursor.close()
        raw_conn.close()

    # log dead row stats after vacuuming
    try:
        stats = _get_dead_row_stats()
        for row in stats:
            logger.info('post-vacuum stats: table=%s live_rows=%s dead_rows=%s '
                        'last_vacuum=%s last_autovacuum=%s',
                        row[0], row[1], row[2], row[3], row[4])
    except Exception as e:
        logger.warning('could not query post-vacuum dead row stats: %s', e)


def epmt_dbcare(retire_jobs=False, vacuum_tables=False, post_process=False, time_limit=None):
    '''
    routine to help regularly take care of the database. for each arg that's true, undertake a cleanup behavior
    retire_jobs will run job retirement. vacuum_tables will run the SQL command VACUUM on jobs, processes, and
    processes_staging, taking care of dead rows. post_process will post process jobs in the database that have
    not yet been associated with data in processes_staging.

    time_limit: float or None
        If set, the maximum number of minutes to spend on dbcare operations.
        The routine will stop cleanly after this duration.
    '''
    job_list=[]

    deadline = None
    if time_limit is not None:
        deadline = time.time() + time_limit * 60
        logger.info('time_limit set to %.1f minutes', time_limit)

    ## RETIRE JOBS
    if not retire_jobs:
        logger.warning('skipping retirement of jobs')
    else:
        logger.info('retiring jobs.')
        epmt_retire(skip_unprocessed=True,
                    dry_run=False,
                    time_limit=time_limit)

    # check deadline after retirement
    if deadline is not None and time.time() >= deadline:
        logger.warning('time limit reached after retirement, stopping')
        return

    ## VACUUM DB TABLES
    if not vacuum_tables:
        logger.warning('skipping vacuuming of tables in DB')
    else:
        _vacuum_tables()

    # check deadline after vacuum
    if deadline is not None and time.time() >= deadline:
        logger.warning('time limit reached after vacuuming, stopping')
        return

    ## POST PROCESS JOBS
    if not post_process:
        logger.warning('skipping post processing of jobs')
    else:
        # postgreSQL statement(s) to count number of unprocessed jobs and retrieve job ids as a list of str
        psql_stub_get_unprocd_jobs="select jobid from jobs where (info_dict -> 'procs_in_process_table')::int = 0"
        psql_get_unprocd_jobs=psql_stub_get_unprocd_jobs + ';'
        psql_count_unprocd_jobs="select COUNT(*) from ( " + psql_stub_get_unprocd_jobs + " ) as my_results;"


        # get count of unprocd jobs and see if there are any to postprocess
        result_count_unprocd_jobs=orm_raw_sql(psql_count_unprocd_jobs)
        number_of_unprocd_jobs=-1
        try:
            number_of_unprocd_jobs=result_count_unprocd_jobs[0][0]
        except Exception as e:
            raise Exception from e

        # check the count of unprocd jobs
        if number_of_unprocd_jobs == 0:
            logger.info('number of unprocessed jobs is 0, nothing to do. exit.')
            raise ValueError('number of unprocessed jobs is 0, nothing to do. exit.')
        if number_of_unprocd_jobs < 0:
            raise ValueError("unable to initialize number of unprocessed jobs, examine code and DB state.")

        logger.info('%s unprocessed jobs found, postprocessing them', number_of_unprocd_jobs)


        # stuff to do! get the jobid list
        result_get_unprocd_jobs=orm_raw_sql(psql_get_unprocd_jobs)
        try:
            logger.info('attempting to retrieve job IDs')
            job_list=[row[0] for row in result_get_unprocd_jobs]
            logger.debug('job_list is %s', ' '.join(job_list))
        except Exception as e:
            raise Exception('problem with retrieving job IDs. inspect code.') from e


        # postprocess the unprocessed jobs
        num_jobs_ppd=len(post_process_jobs(jobs=job_list, deadline=deadline))
        if num_jobs_ppd > 0:
            logger.info('success, num_jobs_ppd = %s', num_jobs_ppd )
        else:
            logger.warning('problem, num_jobs_ppd not greater than 0.')
            logger.warning('num_jobs_ppd = %s', num_jobs_ppd )
