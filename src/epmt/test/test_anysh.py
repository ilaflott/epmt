'''
monolithic tests of epmt start, dump, run, stop, dump, stage, and submit command chain in various shells
'''

import os
from os import environ
import shutil
import unittest

from epmt import epmt_settings as settings
from epmt import epmt_query as eq
from epmt.orm import setup_db
from epmt.epmtlib import timing, capture

jobid = '1011'
tuser = 'testuser'


def do_cleanup():
    for f in ['1', '1.tgz', '1011.tgz']:
        try:
            os.remove(f)
        except OSError:
            pass

    for _d in ['/tmp/epmt']:
        try:
            shutil.rmtree('/tmp/epmt')
        except Exception:
            pass
    eq.delete_jobs(jobid)


@timing
def setUpModule():
    setup_db(settings)
    do_cleanup()

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
        with capture() as (_out, _err):
            results = epmt_run(['sleep 1'], wrapit=True, dry_run=False, debug=False)
            self.assertEqual(0, results)

    def test_monolithic(self):
        from epmt.epmt_cmds import ( epmt_source, epmt_start_job, epmt_dump_metadata,
                                     epmt_run, epmt_stop_job, epmt_stage, epmt_submit )

        with capture() as (_out, _err):
            # Source
            results = epmt_source()
            self.assertIn("PAPIEX_OPTIONS", results, 'epmt_source options are missing')
            self.assertIn("PAPIEX_OUTPUT" , results, 'epmt_source output is missing')
            self.assertIn("LD_PRELOAD"    , results, 'epmt_source ld_preload is missing')

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
            self.assertEqual(os.path.isfile(f'{jobid}.tgz'),
                             1,
                             "epmt_stage output file missing")

            # Submit
            results = epmt_submit([f'{jobid}.tgz'], dry_run=False)
            self.assertTrue(results)


if __name__ == '__main__':
    unittest.main()
