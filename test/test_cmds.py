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
    def test_daemon(self):
        from epmt_daemon import is_daemon_running, start_daemon, \
             print_daemon_status, stop_daemon
        # from warnings import simplefilter
        # simplefilter("ignore", ResourceWarning)
        self.assertFalse(is_daemon_running())
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
            retval, val = epmt_dbsize()
        isPG = (orm_db_provider() == 'postgres')
        self.assertEqual(retval, isPG, 'wrong database return value')

    @unittest.skipUnless(orm_db_provider() == 'postgres', 'requires postgres')
    def test_dbsize_json(self):
        with capture() as (out, err):
            import json
            from epmt_cmds import epmt_dbsize
            retval, out = epmt_dbsize(
                ['database', 'table', 'index', 'tablespace'], usejson=True)
            throws = True
            json.loads(out)
            if len(out) > 1:
                throws = False
        self.assertEqual(throws, False, 'JSON not loaded successfully')

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
