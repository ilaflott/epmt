#!/usr/bin/env python
from __future__ import print_function
import unittest
from glob import glob
from pony.orm import db_session

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

class QueryAPI(unittest.TestCase):
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

    def test_jobs_basic_query(self):
        jobs = eq.get_jobs(fmt='terse')
        self.assertEqual(type(jobs), list, 'wrong jobs format with terse')
        self.assertEqual(len(jobs), 4, 'job count in db wrong')
        df = eq.get_jobs(fmt='pandas')
        self.assertEqual(df.shape, (4, 47), 'wrong jobs dataframe shape')

    @db_session
    def test_procs_query(self):
        jobs = eq.get_jobs(fmt='orm')
        procs = eq.get_procs(fltr=lambda p: 'outlier' in p.job.jobid, fmt='orm')
        self.assertEqual(len(procs), 10600, 'wrong count of processes in ORM format using filter')

        df = eq.get_procs(jobs, limit=5, order='desc(p.duration)', fmt='pandas')
        self.assertEqual(df.shape, (5,49), "incorrect dataframe shape")
        self.assertTrue('outlier' in df.loc[0,'job'], "ordering of processes wrong")

        procs_with_tag = eq.get_procs(jobs, tags='op_sequence:4', fltr='p.duration > 10000000', order='desc(p.duration)', fmt='orm')
        self.assertEqual(len(procs_with_tag), 91, 'incorrect process count when using tags and filter')
        p = procs_with_tag.first()
        self.assertEqual(p.duration, 1008822491.0, 'wrong duration or order when used with tags and filter')
        self.assertEqual(p.descendants.count(), 9548, 'wrong descendant count or order when used with tags and filter')



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
