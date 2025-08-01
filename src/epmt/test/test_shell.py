#!/usr/bin/env python

# the import below is crucial to get a sane test environment
import unittest


class SHELLCmds(unittest.TestCase):
    @unittest.skipUnless(False,
                         'halfbaked unit test never seemed to actually run in the minimal-metrics main/master branch')
    def test_run_cond(self):
        # with capture() as (out,err):
        # import argparse, json
        # argns = argparse.Namespace(auto=True, drop=False, dry_run=False,
        #                           epmt_cmd='dbsize', epmt_cmd_args=['run'],
        #                           error=False, help=False, jobid=None, json=True, verbose=0 )
        from epmt.epmt_cmds import epmt_run
        # pylint: disable=redundant-keyword-arg
        out = epmt_run("1", 'testuser',
                       ["/bin/sleep", "1"],
                       wrapit=True, dry_run=False, debug=False)
        self.assertEqual(out, 0, 'run failed')


if __name__ == '__main__':
    unittest.main()
