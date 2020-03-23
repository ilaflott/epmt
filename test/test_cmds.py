#!/usr/bin/env python

# the import below is crucial to get a sane test environment
from . import *

from epmt_cmds import epmt_dbsize
from epmt_cmd_delete import epmt_delete_jobs
from epmt_cmd_list import  epmt_list_jobs, epmt_list_procs, epmt_list_job_proc_tags, epmt_list_refmodels, epmt_list_op_metrics, epmt_list_thread_metrics


@timing
def setUpModule():
    print('\n' + str(settings.db_params))
    setup_db(settings)
    datafiles='test/data/misc/685000.tgz'
    print('setUpModule: importing {0}'.format(datafiles))
    epmt_submit(glob(datafiles), dry_run=False)
    
#def tearDownModule():

class EPMTCmds(unittest.TestCase):

    @db_session
    def test_daemon(self):
        # We first make sure the DB has one more unanalyzed and
        # and unprocessed jobs. Then we run the daemon loop once.
        # That should clear the backlog of unprocessed and 
        # unanalyzed jobs
        from epmt_daemon import is_daemon_running, daemon_loop
        from epmt_job import post_process_pending_jobs
        self.assertFalse(is_daemon_running())
        if settings.orm == 'sqlalchemy':
            # only sqlalchemy allows this option
            settings.post_process_job_on_ingest = False
        with capture() as (out,err):
            epmt_submit(glob('test/data/daemon/627919.tgz'), dry_run=False)
        settings.post_process_job_on_ingest = True
        up_jobs = eq.get_unprocessed_jobs()
        if settings.orm == 'sqlalchemy':
            self.assertTrue(UnprocessedJob['627919'])
            self.assertTrue(up_jobs)
        self.assertTrue(eq.get_unanalyzed_jobs())
        # a daemon loop should clear the backlog of unprocessed
        # and unanalyzed jobs
        daemon_loop(1)
        self.assertFalse(eq.get_unprocessed_jobs())
        self.assertFalse(eq.get_unanalyzed_jobs())
        # now mark all jobs unanalyzed so future tests aren't affected
        all_jobs = eq.get_jobs(fmt='terse')
        for j in all_jobs:
            eq.remove_job_analyses(j)
        # from warnings import simplefilter
        # simplefilter("ignore", ResourceWarning)
        # rc = start_daemon()
        # self.assertEqual(rc, 0)
        # self.assertTrue(is_daemon_running())
        # with capture() as (out,err):
        #     print_daemon_status()
        # self.assertIn('EPMT daemon running OK', out)
        # rc = stop_daemon()
        # self.assertEqual(rc, 0)
        # self.assertFalse(is_daemon_running())
        # with capture() as (out,err):
        #     print_daemon_status()
        # self.assertEqual('EPMT daemon is not running.', out)
        
    def test_list_jobs(self):
        with capture() as (out,err):
            retval = epmt_list_jobs([])
        self.assertEqual(type(retval), bool, 'wrong list jobs return type')
        self.assertEqual(retval, True, 'wrong list jobs return value')
        with capture() as (out,err):
            retval = epmt_list_jobs(["685000"])
        self.assertEqual(type(retval), bool, 'wrong list jobs return type')
        self.assertEqual(retval, True, 'wrong list jobs return value')
    def test_list_procs(self):
        with capture() as (out,err):
            retval = epmt_list_procs(["685000"])
        self.assertEqual(type(retval), bool, 'wrong list jobs return type')
        self.assertEqual(retval, True, 'wrong list jobs return value')
    def test_list_refmodels(self):
        with capture() as (out,err):
            retval = epmt_list_refmodels('')
        self.assertEqual(retval, False, 'wrong list jobs return value')
    def test_list_op_metrics(self):
        with capture() as (out,err):
            retval = epmt_list_op_metrics(['685000'])
        self.assertTrue(retval, 'wrong list op_metrics return type')
    def test_list_thread_metrics(self):
        p = eq.root('685000', fmt='terse')
        self.assertTrue(p, 'empty root process')
        with capture() as (out,err):
            retval = epmt_list_thread_metrics([p])
        self.assertEqual(type(retval), bool, 'wrong list jobs return type')
        self.assertEqual(retval, True, 'wrong list jobs return value')
    def test_list_job_proc_tags(self):
        with capture() as (out,err):
            retval = epmt_list_job_proc_tags(["685000"])
        self.assertEqual(type(retval), bool, 'wrong list jobs return type')
        self.assertEqual(retval, True, 'wrong list jobs return value')

    def test_dbsize_provider(self):
        with capture() as (out, err):
            from epmt_cmds import epmt_dbsize
            retval = epmt_dbsize()
        isPG = (orm_db_provider() == 'postgres')
        self.assertEqual(retval, isPG, 'wrong database return value')

    @unittest.skipUnless(orm_db_provider() == 'postgres', 'requires postgres')
    def test_dbsize_json(self):
        with capture() as (out, err):
            import json
            from epmt_cmds import epmt_dbsize
            retval = epmt_dbsize(
                ['database', 'table', 'index', 'tablespace'], usejson=True)
            throws = True
            json.loads(out)
            if len(out) > 1:
                throws = False
        self.assertEqual(throws, False, 'JSON not loaded successfully')

    def test_yy_retire(self):
        from datetime import datetime, timedelta
        org_jobs = eq.get_jobs(fmt='terse')
        self.assertTrue('627919' in org_jobs)
        # ndays = (datetime.now() - datetime(2019,6,15,7,52)).days # days since start of 685000 
        # Job 627919 start: 2019-06-10 06:23:08.427666-04:00
        ndays = (datetime.now() - datetime(2019,6,10,6,23)).days
        org_setting = settings.retire_jobs_ndays
        settings.retire_jobs_ndays = ndays - 1 # to make sure we retire 627919
        from epmt_cmd_retire import epmt_retire
        with capture() as (out,err):
            (jobs_delete_count, _) = epmt_retire()
        settings.retire_jobs_ndays = org_setting # restore original setting
        self.assertTrue(jobs_delete_count > 0)
        jobs = eq.get_jobs(fmt='terse')
        self.assertFalse('627919' in jobs)

    def test_zz_drop_db(self):
        jobs = eq.get_jobs(fmt='terse')
        self.assertTrue(len(jobs) > 0)
        from orm import orm_drop_db
        with capture() as (out,err):
            orm_drop_db()
        jobs = eq.get_jobs(fmt='terse')
        self.assertEqual(len(jobs), 0)

if __name__ == '__main__':
    unittest.main()
