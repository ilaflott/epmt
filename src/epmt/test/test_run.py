#!/usr/bin/env python

import unittest
import os
from epmt.orm import setup_db
from epmt.epmtlib import get_username, timing
import epmt.epmt_settings as settings
# import os


def remove_stale_files():
    for f in ['1', '1.tgz']:
        try:
            os.remove(f)
        except OSError:
            pass
    import shutil
    for d in ['/tmp/epmt']:
        try:
            shutil.rmtree('/tmp/epmt')
        except Exception:
            pass


def remove_jobid_envs():
    from os import environ
    for e in settings.jobid_env_list:
        jid = environ.get(e)
        if jid and len(jid) > 0:
            del environ[e]


# These will be used in both tests
# One can embed them in the class, but referring to them with
# a class prefix is ugly
jobid = '1011'
tuser = 'testuser'
odir = settings.epmt_output_prefix + get_username() + "/"


@timing
def setUpModule():
    setup_db(settings)
#    print('\n' + str(settings.db_params))
    remove_stale_files()
    from os import environ
    environ['SLURM_JOB_USER'] = tuser
    # environ['SLURM_JOB_ID'] = jobid


def tearDownModule():
    remove_stale_files()


class EPMTShell(unittest.TestCase):
    # Test epmt with run argument
    def test_run_auto(self):
        from epmt.epmt_cmds import epmt_run
        from os import environ
        environ['SLURM_JOB_ID'] = jobid
        remove_stale_files()
        with capture() as (out, err):
            results = epmt_run(['sleep 1'], wrapit=True, dry_run=False, debug=False)

        self.assertTrue(jobid in os.listdir(odir))
        self.assertEqual(0, results)
    # Test run with a slurm job id env

    def test_run_slurm_jobid(self):
        remove_jobid_envs()
        from os import environ
        environ['SLURM_JOB_ID'] = jobid
        from epmt.epmt_cmds import epmt_run
        remove_stale_files()
        with capture() as (out, err):
            results = epmt_run(['sleep 1'], wrapit=True, dry_run=False, debug=False)
            self.assertTrue(jobid in os.listdir(odir))
            self.assertEqual(0, results)
    # Test run with a slurm pb job id

    def test_run_pbjobid(self):
        remove_jobid_envs()
        from os import environ
        environ['PBS_JOB_ID'] = jobid
        from epmt.epmt_cmds import epmt_run
        remove_stale_files()
        with capture() as (out, err):
            results = epmt_run(['sleep 1'], wrapit=True, dry_run=False, debug=False)
            self.assertTrue(jobid in os.listdir(odir))
            self.assertEqual(0, results)
    # Test run for missing jobid

    def test_run_no_jobid(self):
        # remove_jobid_envs()
        from epmt.epmt_cmds import epmt_run
        remove_stale_files()
        # quell the error messages
        epmt_logging_init(-2)
        with capture() as (out, err):
            results = epmt_run(['sleep 1'], wrapit=True, dry_run=False, debug=False)
            self.assertEqual(1, results)
        # restore logging level
        epmt_logging_init(-1)
    # A dry run should not create an output directory

    def test_run_dry_run(self):
        remove_jobid_envs()
        from os import environ
        environ['SLURM_JOB_ID'] = jobid
        from epmt.epmt_cmds import epmt_run
        remove_stale_files()
        with capture() as (out, err):
            results = epmt_run(['sleep 1'], wrapit=True, dry_run=True, debug=False)
            self.assertFalse(os.path.isdir(settings.epmt_output_prefix))
            self.assertEqual(0, results)

    def test_run_dry_run_missing_jid(self):
        remove_jobid_envs()
        # from os import environ
        # environ['SLURM_JOB_ID'] = jobid
        from epmt.epmt_cmds import epmt_run
        remove_stale_files()
        # quell the error messages
        epmt_logging_init(-2)
        with capture() as (out, err):
            results = epmt_run(['sleep 1'], wrapit=True, dry_run=True, debug=False)
            self.assertEqual(1, results)
        # restore logging level
        epmt_logging_init(-1)

    def test_run_nowrap(self):
        remove_jobid_envs()
        from os import environ
        environ['SLURM_JOB_ID'] = jobid
        from epmt.epmt_cmds import epmt_run
        remove_stale_files()
        with capture() as (out, err):
            results = epmt_run(['sleep 1'], wrapit=False, dry_run=False, debug=False)
            self.assertEqual(0, results)

    def test_monolithic(self):
        from epmt.epmt_cmds import epmt_check, epmt_source, epmt_start_job, epmt_dump_metadata, epmt_run
        remove_jobid_envs()
        from os import environ
        environ['SLURM_JOB_ID'] = jobid
        environ['SLURM_JOB_USER'] = tuser
        with capture() as (out, err):
            # Check will fail because of kernel paranoid, but we can't be
            # sure it will always fail.
            # TODO: Fix this so we can count on it to either always fail or always
            # pass. Since we can't count on the kernel paranoid setting to be right,
            # it might be better to set this up to always fail. But how?
            # results = epmt_check()
            # self.assertEqual(results, False)

            # Source
            results = epmt_source()
            self.assertIn("PAPIEX_OPTIONS", results, 'epmt_source options are missing')
            self.assertIn("PAPIEX_OUTPUT", results, 'epmt_source output is missing')
            self.assertIn("LD_PRELOAD", results, 'epmt_source ld_preload is missing')

            # Run
            results = epmt_run(['sleep 1'], wrapit=True, dry_run=False, debug=False)
            self.assertTrue(jobid in os.listdir(odir))
            self.assertEqual(0, results, 'epmt_run returned False')


if __name__ == '__main__':
    unittest.main()
