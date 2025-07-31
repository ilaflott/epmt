#!/usr/bin/env python

# the import below is crucial to get a sane test environment
import unittest
from datetime import datetime
from shutil import copytree
from epmt.orm import UnprocessedJob, db_session, setup_db
from epmt.epmtlib import capture, timing
import epmt.epmt_settings as settings

from epmt.epmt_cmds import epmt_dbsize
from epmt.epmt_cmd_delete import epmt_delete_jobs
from epmt.epmt_cmd_list import (epmt_list_jobs, epmt_list_procs, epmt_list_job_proc_tags,
                                epmt_list_refmodels, epmt_list_op_metrics, epmt_list_thread_metrics)
from epmt.epmt_daemon import is_daemon_running, daemon_loop

# from epmt.orm.sqlalchemy.models import UnprocessedJob
# from os import path


def do_cleanup():
    eq.delete_jobs(['685000', '627919', '691201', '692544'], force=True, remove_models=True)
#    eq.delete_jobs(['685000', '685016', '627919', '691201', '692544'], force=True, remove_models = True)


@timing
def setUpModule():
    #    print('\n' + str(settings.db_params))
    setup_db(settings)
    do_cleanup()
    datafiles = '{}/test/data/misc/685000.tgz'.format(install_root)
#    datafiles='{}/test/data/misc/685???.tgz'.format(install_root)
    print('setUpModule: submitting to db {0}'.format(datafiles))
    settings.post_process_job_on_ingest = True
    with capture() as (out, err):
        epmt_submit(glob(datafiles), dry_run=False)
    settings.post_process_job_on_ingest = False
    assert eq.get_jobs(['685000'], fmt='terse') == ['685000']
#    assert eq.get_jobs(['685016'], fmt='terse') == ['685016']
    assert eq.get_unprocessed_jobs() == []


def tearDownModule():
    do_cleanup()


class EPMTCmds(unittest.TestCase):

    def test_get_papiex_options(self):
        from epmt.epmt_cmds import get_papiex_options
        from socket import gethostname
        from cpuinfo import get_cpu_info
        cpu_info = get_cpu_info()
        cpu_fms = str(cpu_info.get('family', 'no_family_found')) + "/" + \
            str(cpu_info.get('model', 'no_model_found')) + "/" + \
            str(cpu_info.get('stepping', 'no_stepping_found'))

        class S:
            def __init__(self):
                self.papiex_options_byhost = dict({gethostname(): "MATCH1"})
                self.papiex_options_bycpu = dict({cpu_fms: "MATCH2"})
                self.papiex_options = "DEFAULT"

            def __repr__(self):
                return 'self.papiex_options_byhost = \n' + str(self.papiex_options_byhost) + \
                    '\nself.papiex_options_bycpu = \n' + str(self.papiex_options_bycpu) + \
                    '\nself.papiex_options = \n' + str(self.papiex_options)

        s = S()
        opts = get_papiex_options(s)
        self.assertTrue("MATCH1" in opts and "MATCH2" in opts and "DEFAULT" in opts)

        cpu_fms = \
            str(cpu_info.get('family', 'no_family_found')) + "/" + ".*" + "/" + \
            str(cpu_info.get('stepping', 'no_stepping_found'))
        s.papiex_options_bycpu = dict({cpu_fms: "MATCH3"})
        opts = get_papiex_options(s)
        self.assertTrue("MATCH1" in opts and "MATCH3" in opts and "DEFAULT" in opts)

        s.papiex_options_byhost = dict({".*": "MATCH4"})
        opts = get_papiex_options(s)
        self.assertTrue("MATCH4" in opts and "MATCH3" in opts and "DEFAULT" in opts)

        s.papiex_options_byhost = dict({"*": "MATCH5"})

        # this is throwing an error:
        #     "Invalid regular expression in papiex_options_byhost: key is *, value is MATCH5."
        # digging deeper gives us an error from re.match:
        #     "nothing to repeat at position 0"
        # this seems to be intentional. real question is why isnt logging working as desired? apparently. i digress.
        # print("A")
        # quell the error messages
        epmt_logging_init(-2)
        # print("B")
        # print("s = ", s.__repr__())
        opts = get_papiex_options(s)
        # print("C")
        # print(opts)
        epmt_logging_init(-1)
        # print("D")
        # print("opts is ", opts)
        self.assertTrue("MATCH5" not in opts)

    @db_session
    def test_daemon_ingest(self):
        self.assertFalse(eq.orm_get(eq.Job, '691201') or eq.orm_get(eq.Job, '692544'))

        # now start 1 iteration of the daemon code
        # watching the directory containing the .tgz
        # This should result in one unprocessed job in the database
        settings.post_process_job_on_ingest = False
        with capture() as (out, err):
            self.assertFalse(daemon_loop(
                nullcontext(), niters=1, ingest='{}/test/data/daemon/ingest'.format(install_root),
                post_process=False, analyze=False, retire=False, keep=True, recursive=False))

        # by now the files should be in the DB
        # logger.error("What the....jobs now in DB"+str(eq.get_jobs(fmt='terse')))
        self.assertEqual(set(eq.get_jobs(['691201', '692544'], fmt='terse')), set({'691201', '692544'}))

        # make sure the files aren't removed (since we used the "keep" option)
        self.assertTrue(path.exists('{}/test/data/daemon/ingest/691201.tgz'.format(install_root)))
        self.assertTrue(path.exists('{}/test/data/daemon/ingest/692544.tgz'.format(install_root)))

#    @unittest.skipIf(len(eq.get_unprocessed_jobs()) == 0, 'unprocessed jobs in database')
    @db_session
    def test_daemon_post_process(self):
        # We first make sure the DB has one more unanalyzed and
        # and unprocessed jobs. Then we run the daemon loop once.
        # That should clear the backlog of unprocessed and
        # unanalyzed jobs
        from epmt.epmt_job import post_process_pending_jobs
        self.assertTrue(is_daemon_running() == (False, -1))

        settings.post_process_job_on_ingest = False
        with capture() as (out, err):
            self.assertTrue(epmt_submit(glob('{}/test/data/daemon/627919.tgz'.format(install_root)), dry_run=False))

        up_jobs = eq.get_unprocessed_jobs()
        self.assertTrue(UnprocessedJob['627919'])
        self.assertTrue(up_jobs)
        self.assertTrue(eq.get_unanalyzed_jobs())

        # a daemon loop should clear the backlog of unprocessed
        # and unanalyzed jobs
        #       with capture() as (out,err):
        with capture() as (out, err):
            self.assertFalse(daemon_loop(
                nullcontext(), niters=1, ingest=False,
                post_process=True, analyze=False, retire=False, keep=True, recursive=False))
        self.assertFalse(eq.get_unprocessed_jobs())
        self.assertFalse(eq.get_unanalyzed_jobs() == [])

        # now mark all jobs unanalyzed so future tests aren't affected
        # all_jobs = eq.get_jobs(fmt='terse')
        # for j in all_jobs:
        #    eq.remove_job_analyses(j)

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
        with capture() as (out, err):
            retval = epmt_list_jobs([])
        self.assertEqual(type(retval), bool, 'wrong list jobs return type')
        self.assertEqual(retval, True, 'wrong list jobs return value')

        with capture() as (out, err):
            retval = epmt_list_jobs(["685000"])
        self.assertEqual(type(retval), bool, 'wrong list jobs return type')
        self.assertEqual(retval, True, 'wrong list jobs return value')

    def test_list_procs(self):
        with capture() as (out, err):
            retval = epmt_list_procs(["685000"])
        self.assertEqual(type(retval), bool, 'wrong list jobs return type')
        self.assertEqual(retval, True, 'wrong list jobs return value')

    def test_list_refmodels(self):
        with capture() as (out, err):
            retval = epmt_list_refmodels('')
        self.assertEqual(retval, False, 'wrong list jobs return value')

    def test_list_op_metrics(self):
        with capture() as (out, err):
            retval = epmt_list_op_metrics(['685000'])
        self.assertTrue(retval, 'wrong list get_op_metrics return type')

    def test_list_thread_metrics(self):
        p = eq.root('685000', fmt='terse')
        self.assertTrue(p, 'empty root process')
        with capture() as (out, err):
            retval = epmt_list_thread_metrics([p])
        self.assertEqual(type(retval), bool, 'wrong list jobs return type')
        self.assertEqual(retval, True, 'wrong list jobs return value')

    def test_list_job_proc_tags(self):
        with capture() as (out, err):
            retval = epmt_list_job_proc_tags(["685000"])
        self.assertEqual(type(retval), bool, 'wrong list jobs return type')
        self.assertEqual(retval, True, 'wrong list jobs return value')

    def test_dbsize_json(self):
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
            self.assertTrue(d)
            self.assertEqual(type(d), dict, "wrong return type")
            self.assertTrue(len(d.keys()) > 0)

    def test_stage(self):
        from epmt.epmt_cmds import epmt_stage
        # quell the error messages
        epmt_logging_init(-2)

        from os import remove, path
        from shutil import copytree, rmtree
        from tempfile import gettempdir, mkdtemp
        # re-create error file if it's still hanging around and we didnt clean up lasttime
        errorfile = settings.error_dest + '/pp053-papiex-615503-0.csv.error'
        if path.exists(errorfile):
            remove(errorfile)
        tempdir = mkdtemp(prefix='epmt_', dir=gettempdir())
        copytree("{}/test/data/corrupted_csv".format(install_root), tempdir + "/corrupted_csv")
        with capture() as (out, err):
            retval = epmt_stage([tempdir + "/corrupted_csv"], keep_going=False)
        self.assertTrue(retval == False, "corrupted CSV files, should have returned False")
        self.assertFalse(path.exists(errorfile))

        # cleanup
        rmtree(tempdir + "/corrupted_csv")
        rmtree(tempdir)
        if path.exists(errorfile):
            remove(errorfile)

        tempdir = mkdtemp(prefix='epmt_', dir=gettempdir())
        copytree("{}/test/data/corrupted_csv".format(install_root), tempdir + "/corrupted_csv")
        with capture() as (out, err):
            retval = epmt_stage([tempdir + "/corrupted_csv"], keep_going=True)
        self.assertTrue(retval, "corrupted CSV files but keep_going, should have returned True")
        self.assertTrue(path.exists(errorfile))
        self.assertFalse(path.exists(tempdir + "/corrupted_csv"))

        # cleanup + logging level restoration
        remove(errorfile)
        remove('corrupted_csv.tgz')
        rmtree(tempdir)
        epmt_logging_init(-1)

    def test_yyy_retire(self):
        from datetime import datetime, timedelta
        # with capture() as (out,err):
        #    epmt_submit(glob('{}/test/data/daemon/627919.tgz'.format(install_root)), dry_run=False)
        org_jobs = eq.get_jobs(["685000"], fmt='dict')
        self.assertTrue(org_jobs)

        # the current age of the test job
        ndays = (datetime.now() - datetime(2019, 6, 15, 7, 52, 4)).days
        org_setting = settings.retire_jobs_ndays

        # to make sure we retire 627919, set retirement to it's age minus a day
        settings.retire_jobs_ndays = ndays - 1
        from epmt.epmt_cmd_retire import epmt_retire
        with capture() as (out, err):
            (jobs_delete_count, _) = epmt_retire()

        # restore original setting
        settings.retire_jobs_ndays = org_setting
        self.assertTrue(jobs_delete_count > 0)

        # confirm the job was retired
        jobs = eq.get_jobs(fmt='terse')
        print(f'jobs = {jobs}')
        self.assertFalse('685000' in jobs)

    @unittest.skipUnless(orm_in_memory(), 'skip on persistent database')
    def test_zz_drop_db(self):
        # submit a job to the db we just cleaned out... oops!
        datafiles = '{}/test/data/misc/685000.tgz'.format(install_root)
        #        settings.post_process_job_on_ingest = True
        with capture() as (out, err):
            epmt_submit(glob(datafiles), dry_run=False)
        #        settings.post_process_job_on_ingest = False

        # check that we get a list job nums as strs in a list
        jobs = eq.get_jobs(fmt='terse')
        self.assertTrue(len(jobs) > 0)

        # drop the db and check that we get an empty list after dropping the db
        from epmt.orm import orm_drop_db
        with capture() as (out, err):
            orm_drop_db()
        jobs = eq.get_jobs(fmt='terse')
        self.assertEqual(len(jobs), 0)


if __name__ == '__main__':
    unittest.main()
