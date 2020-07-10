#!/usr/bin/env python

# the import below is crucial to get a sane test environment
from . import *

from epmt_cmds import epmt_dbsize
from epmt_cmd_delete import epmt_delete_jobs
from epmt_cmd_list import  epmt_list_jobs, epmt_list_procs, epmt_list_job_proc_tags, epmt_list_refmodels, epmt_list_op_metrics, epmt_list_thread_metrics


def do_cleanup():
    eq.delete_jobs(['685000', '627919', '691201', '692544'], force=True, remove_models = True)

@timing
def setUpModule():
    print('\n' + str(settings.db_params))
    setup_db(settings)
    do_cleanup()
    datafiles='{}/test/data/misc/685000.tgz'.format(install_root)
    print('setUpModule: importing {0}'.format(datafiles))
    epmt_submit(glob(datafiles), dry_run=False)
    
def tearDownModule():
    do_cleanup()

class EPMTCmds(unittest.TestCase):

    def test_get_papiex_options(self):
        from epmt_cmds import get_papiex_options
        from socket import gethostname
        from ls_cpu_info import get_cpu_info
        cpu_info = get_cpu_info()
        cpu_fms = str(cpu_info['family']) + "/" + str(cpu_info['model']) + "/" + str(cpu_info['stepping'])
        class S:
            def __init__(self):
                self.papiex_options_byhost = dict({gethostname(): "MATCH1"})
                self.papiex_options_bycpu = dict({cpu_fms: "MATCH2"})
                self.papiex_options = "DEFAULT"
        s = S()
        opts = get_papiex_options(s)
        self.assertTrue("MATCH1" in opts and "MATCH2" in opts and "DEFAULT" in opts)
        cpu_fms = str(cpu_info['family']) + "/" + ".*" + "/" + str(cpu_info['stepping'])
        s.papiex_options_bycpu = dict({cpu_fms: "MATCH3"})
        opts = get_papiex_options(s)
        self.assertTrue("MATCH1" in opts and "MATCH3" in opts and "DEFAULT" in opts)
        s.papiex_options_byhost = dict({".*": "MATCH4"})
        opts = get_papiex_options(s)
        self.assertTrue("MATCH4" in opts and "MATCH3" in opts and "DEFAULT" in opts)
        s.papiex_options_byhost = dict({"*": "MATCH5"})
        # quell the error messages
        epmt_logging_init(-2)
        opts = get_papiex_options(s)
        epmt_logging_init(-1)
        self.assertTrue("MATCH5" not in opts)
        
    @db_session
    def test_daemon_ingest(self):
        from epmt_daemon import daemon_loop
        from os import path
        self.assertFalse(eq.orm_get(eq.Job, '691201') or eq.orm_get(eq.Job, '692544'))
        # now start the daemon and make it watch the directory containing the .tgz
        with capture() as (out,err):
            # use daemon solely for ingest
            daemon_loop(1, ingest='{}/test/data/daemon/ingest'.format(install_root), post_process=False, retire=False, keep=True, recursive=False)
        # by now the files should be in the DB
        self.assertEqual(set(eq.get_jobs(['691201', '692544'], fmt='terse')), {'691201', '692544'})
        # make sure the files aren't removed (since we used the "keep" option)
        self.assertTrue(path.exists('{}/test/data/daemon/ingest/691201.tgz'.format(install_root)) and path.exists('{}/test/data/daemon/ingest/692544.tgz'.format(install_root)))

    @unittest.skipIf(eq.get_unprocessed_jobs(), 'unprocessed jobs in database')
    @db_session
    def test_daemon_post_process(self):
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
            epmt_submit(glob('{}/test/data/daemon/627919.tgz'.format(install_root)), dry_run=False)
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
        self.assertTrue(retval, 'wrong list get_op_metrics return type')
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


    def test_dbsize_json(self):
        from epmt_cmds import epmt_dbsize
        with capture() as (out, err):
            retval = epmt_dbsize(['database', 'table', 'index', 'tablespace'], usejson=True)
        s = out.getvalue()
        isPG = (orm_db_provider() == 'postgres')
        self.assertEqual(retval, isPG, 'wrong epmt_dbsize() return value')
        # on postgres we actually get a long string output
        if isPG:
            self.assertTrue(len(s) > 0)
            from json import loads
            d = loads(s)
            self.assertTrue(d != False)
            self.assertEqual(type(d), dict, "wrong return type")
            self.assertTrue(len(d.keys()) > 0)

  
    def test_stage(self):
        from epmt_cmds import epmt_stage
        # quell the error messages
        epmt_logging_init(-2)
        from os import remove, path
        from shutil import copytree, rmtree
        from tempfile import gettempdir, mkdtemp

        errorfile=settings.error_dest+'/pp053-papiex-615503-0.csv.error'
        if path.exists(errorfile):
            remove(errorfile)
        tempdir = mkdtemp(prefix='epmt_',dir=gettempdir())
        copytree("{}/test/data/corrupted_csv".format(install_root),tempdir+"/corrupted_csv")
        with capture() as (out, err):
            retval = epmt_stage([tempdir+"/corrupted_csv"],keep_going=False)
        self.assertTrue(retval == False, "corrupted CSV files, should have returned False")
        self.assertFalse(path.exists(errorfile))
        rmtree(tempdir+"/corrupted_csv")
        rmtree(tempdir)
        
        if path.exists(errorfile):
            remove(errorfile)
        tempdir = mkdtemp(prefix='epmt_',dir=gettempdir())
        copytree("{}/test/data/corrupted_csv".format(install_root),tempdir+"/corrupted_csv")
        with capture() as (out, err):
            retval = epmt_stage([tempdir+"/corrupted_csv"],keep_going=True)
        self.assertTrue(retval == True, "corrupted CSV files but keep_going, should have returned True")
        self.assertTrue(path.exists(errorfile))
        self.assertFalse(path.exists(tempdir+"/corrupted_csv"))
        remove(errorfile) # cleanup after ourselves
        remove('corrupted_csv.tgz')
        rmtree(tempdir)
        # restore logging level
        epmt_logging_init(-1)
        
    def test_yy_retire(self):
        from datetime import datetime, timedelta
        with capture() as (out,err):
            epmt_submit(glob('{}/test/data/daemon/627919.tgz'.format(install_root)), dry_run=False)
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

    @unittest.skipUnless(orm_in_memory(), 'skip on persistent database')
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
