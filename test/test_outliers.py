#!/usr/bin/env python
from __future__ import print_function
import unittest
from glob import glob

# put this above all epmt imports so they use defaults
from os import environ
environ['EPMT_USE_DEFAULT_SETTINGS'] = "1"

from epmt_cmds import set_logging, epmt_submit
set_logging(0)

import epmt_query as eq
import epmt_outliers as eod
from epmtlib import timing


@timing
def setUpModule():
    epmt_submit(glob('test/data/outliers/*.tgz'), dry_run=False)
    

def tearDownModule():
    pass

class TestOutliers(unittest.TestCase):
    # called ONCE before before first test in this class starts
    @classmethod
    def setUpClass(cls):
        pass

    # called ONCE after last tests in this class is finished
    @classmethod
    def tearDownClass(cls):
        pass

    # called before every test
    def setUp(self):
        pass

    # called after every test
    def tearDown(self):
        pass

    def test_num_jobs(self):
        self.assertEqual(len(eq.get_jobs(fmt='terse')), 4, 'job count in db wrong')

    def test_outlier_jobs(self):
        jobs = eq.get_jobs(fmt='orm')
        df = eod.detect_outlier_jobs(jobs)
        self.assertEqual(len(df[df.duration > 0]), 1, "incorrect count of duration outliers")
        self.assertEqual(len(df[df.cpu_time > 0]), 1, "incorrect count of cpu_time outliers")
        self.assertEqual(len(df[df.num_procs > 0]), 0, "incorrect count of num_procs outliers")
        self.assertTrue('outlier' in df[df.duration > 0]['jobid'].values[0], "wrong duration outlier")
        self.assertTrue('outlier' in df[df.cpu_time > 0]['jobid'].values[0], "wrong duration outlier")


if __name__ == '__main__':
    unittest.main()
    #suite = unittest.TestLoader().loadTestsFromTestCase(TestStringMethods)
    #unittest.TextTestRunner(verbosity=2).run(suite)
