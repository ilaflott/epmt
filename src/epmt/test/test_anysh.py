#!/usr/bin/env python

import unittest
from os import environ
from epmt.epmtlib import capture, timing
from epmt.orm import setup_db
import epmt.epmt_settings as settings
# import os

# These will be used in both tests
# One can embed them in the class, but referring to them with
# a class prefix is ugly
jobid = '1011'
tuser = 'testuser'


def do_cleanup():
    for f in ['1', '1.tgz', '1011.tgz']:
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
    eq.delete_jobs(jobid)


@timing
def setUpModule():
    setup_db(settings)
#    print('\n' + str(settings.db_params))
    do_cleanup()
    from os import environ
    environ['SLURM_JOB_ID'] = jobid
    environ['SLURM_JOB_USER'] = tuser
    settings.post_process_job_on_ingest = True


def tearDownModule():
    settings.post_process_job_on_ingest = False
    do_cleanup()


class EPMTShell(unittest.TestCase):

    def test_run_auto(self):
        from epmt.epmt_cmds import epmt_run
        do_cleanup()
        with capture() as (out, err):
            results = epmt_run(['sleep 1'], wrapit=True, dry_run=False, debug=False)
            self.assertEqual(0, results)

    def test_monolithic(self):
        from epmt.epmt_cmds import epmt_check, epmt_source, epmt_start_job, epmt_dump_metadata, epmt_run, epmt_stop_job, epmt_stage, epmt_submit
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

            # Start
            results = epmt_start_job()
            self.assertTrue(results)

            # Dump
            results = epmt_dump_metadata([])
            self.assertTrue(results)

            # Run
            results = epmt_run(['sleep 1'], wrapit=False, dry_run=False, debug=False)
            self.assertEqual(0, results, 'epmt_run returned False')

            # Stop
            results = epmt_stop_job()
            self.assertTrue(results)

            # Dump
            results = epmt_dump_metadata([])
            self.assertTrue(results)

            # Stage
            results = epmt_stage([])  # ['/tmp/epmt/' + tuser + '/epmt/'+jobid+'/'])
            self.assertTrue(results)
            self.assertEqual(os.path.isfile(jobid + '.tgz'), 1, "epmt_stage output file missing")

            # Submit
            results = epmt_submit([jobid + '.tgz'], dry_run=False)
            self.assertTrue(results)


if __name__ == '__main__':
    unittest.main()
