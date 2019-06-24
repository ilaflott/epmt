#!/usr/bin/env python
from __future__ import print_function
import unittest
from sys import stderr, exit
from glob import glob
from pony.orm import db_session
from models import db

# put this above all epmt imports so they use defaults
from os import environ
environ['EPMT_USE_DEFAULT_SETTINGS'] = "1"

from epmt_job import setup_orm_db
from epmt_cmds import set_logging, epmt_submit
set_logging(-1)

import epmt_query as eq
import epmt_outliers as eod
from epmtlib import timing
import epmt_default_settings as settings

@timing
def setUpModule():
    if settings.db_params.get('filename') != ':memory:':
        print('db_params MUST use in-memory sqlite for testing', file=stderr)
        exit(1)
    setup_orm_db(settings, drop=True)
    datafiles='test/data/outliers/*.tgz'
    print('setUpModule: importing {0}'.format(datafiles))
    epmt_submit(glob(datafiles), dry_run=False)

def tearDownModule():
    pass

class OutliersAPI(unittest.TestCase):
##    # called ONCE before before first test in this class starts
##    @classmethod
##    def setUpClass(cls):
##        pass
##
##    # called ONCE after last tests in this class is finished
##    @classmethod
##    def tearDownClass(cls):
##        pass
##
##    # called before every test
##    def setUp(self):
##        pass
##
##    # called after every test
##    def tearDown(self):
##        pass

    @db_session
    def test_outlier_jobs(self):
        jobs = eq.get_jobs(tag='exp_name:linux_kernel', fmt='orm')
        (df, parts) = eod.detect_outlier_jobs(jobs)
        self.assertEqual(len(df[df.duration > 0]), 1, "incorrect count of duration outliers")
        self.assertEqual(len(df[df.cpu_time > 0]), 1, "incorrect count of cpu_time outliers")
        self.assertEqual(len(df[df.num_procs > 0]), 0, "incorrect count of num_procs outliers")
        self.assertTrue('outlier' in df[df.duration > 0]['jobid'].values[0], "wrong duration outlier")
        self.assertTrue('outlier' in df[df.cpu_time > 0]['jobid'].values[0], "wrong duration outlier")
        self.assertEqual(len(parts), 3, "wrong number of items in partition dictionary")
        self.assertEqual(parts['duration'], (set([u'kern-6656-20190614-190245', u'kern-6656-20190614-194024', u'kern-6656-20190614-191138']), set([u'kern-6656-20190614-192044-outlier'])))

    @db_session
    def test_outlier_ops(self):
        jobs = eq.get_jobs(tag='exp_name:linux_kernel', fmt='orm')
        (df, parts) = eod.detect_outlier_ops(jobs)
        self.assertEqual(df.shape, (20,5), "wrong shape of df from detect_outlier_ops")
        self.assertEqual(len(df[df.duration > 0]), 3, 'wrong outlier count for duration')
        self.assertEqual(len(df[df.cpu_time > 0]), 5, 'wrong outlier count for cpu_time')
        self.assertEqual(len(df[df.num_procs > 0]), 0, 'wrong outlier count for num_procs')
        self.assertEqual(list(df.loc[2].values), [u'kern-6656-20190614-192044-outlier', {u'op_instance': u'4', u'op_sequence': u'4', u'op': u'build'}, 1, 1, 0])
        self.assertEqual(len(parts), 5, 'wrong number of distinct tags')
        self.assertEqual(parts['{"op_instance": "4", "op_sequence": "4", "op": "build"}'], (set([u'kern-6656-20190614-190245', u'kern-6656-20190614-191138', u'kern-6656-20190614-194024']), set([u'kern-6656-20190614-192044-outlier'])))

        (df, parts) = eod.detect_outlier_ops(jobs, tags = {"op_instance": "4", "op_sequence": "4", "op": "build"})
        self.assertEqual(df.shape, (4,5), "wrong shape of df from detect_outlier_ops with supplied tag")
        self.assertEqual(list(df.duration), [0, 0, 1, 0])
        self.assertEqual(list(df.cpu_time), [0, 0, 1, 0])
        self.assertEqual(list(df.num_procs), [0, 0, 0, 0])
        self.assertEqual(parts, {'{"op_instance": "4", "op_sequence": "4", "op": "build"}': (set([u'kern-6656-20190614-190245', u'kern-6656-20190614-191138', u'kern-6656-20190614-194024']), set([u'kern-6656-20190614-192044-outlier']))})


    @db_session
    def test_partition_jobs(self):
        jobs = eq.get_jobs(tag='launch_id:6656', fmt='orm')
        self.assertEqual(jobs.count(), 4, "incorrect job count using tags")
        parts = eod.partition_jobs(jobs, fmt='terse')
        self.assertEqual(len(parts), 3, "incorrect count of items in partition dict")
        self.assertEqual(parts['cpu_time'], (set([u'kern-6656-20190614-190245', u'kern-6656-20190614-194024', u'kern-6656-20190614-191138']), set([u'kern-6656-20190614-192044-outlier'])))
        self.assertEqual(parts['duration'], (set([u'kern-6656-20190614-190245', u'kern-6656-20190614-194024', u'kern-6656-20190614-191138']), set([u'kern-6656-20190614-192044-outlier'])))
        self.assertEqual(parts['num_procs'], (set([u'kern-6656-20190614-190245', u'kern-6656-20190614-192044-outlier', u'kern-6656-20190614-194024', u'kern-6656-20190614-191138']), set([])))

    @db_session
    def test_partition_jobs_by_ops(self):
        jobs = eq.get_jobs(fmt='terse', tag='exp_name:linux_kernel')
        parts = eod.partition_jobs_by_ops(jobs)
        self.assertEqual(len(parts), 5, "incorrect number of tags in output")
        self.assertEqual(parts['{"op_instance": "3", "op_sequence": "3", "op": "configure"}'], (set([u'kern-6656-20190614-190245', u'kern-6656-20190614-191138', u'kern-6656-20190614-194024']), set([u'kern-6656-20190614-192044-outlier'])), "wrong partitioning for configure op")
        parts = eod.partition_jobs_by_ops(jobs, tags = 'op:build;op_instance:4;op_sequence:4')
        self.assertEqual(parts, {'{"op_instance": "4", "op_sequence": "4", "op": "build"}': (set([u'kern-6656-20190614-190245', u'kern-6656-20190614-191138', u'kern-6656-20190614-194024']), set([u'kern-6656-20190614-192044-outlier']))}, "wrong partitioning when supplying a single tag string")
        parts = eod.partition_jobs_by_ops(jobs, tags = ['op:build;op_instance:4;op_sequence:4', {"op_instance": "2", "op_sequence": "2", "op": "extract"}])
        self.assertEqual(parts, {'{"op_instance": "4", "op_sequence": "4", "op": "build"}': (set([u'kern-6656-20190614-190245', u'kern-6656-20190614-191138', u'kern-6656-20190614-194024']), set([u'kern-6656-20190614-192044-outlier'])), '{"op_instance": "2", "op_sequence": "2", "op": "extract"}': (set([u'kern-6656-20190614-190245', u'kern-6656-20190614-191138', u'kern-6656-20190614-194024']), set([u'kern-6656-20190614-192044-outlier']))}, "wrong partitioning when supplying tags consisting of a list of string and dict")
        

    @db_session
    def test_rca_jobs(self):
        ref_jobs = eq.get_jobs(tag='exp_name:linux_kernel', fltr='"outlier" not in j.jobid', fmt='orm')
        outlier_job = eq.get_jobs(tag='exp_name:linux_kernel', fltr='"outlier" in j.jobid', fmt='orm')
        (res, df, sl) = eod.detect_rootcause(ref_jobs, outlier_job)
        self.assertTrue(res, 'detect_rootcause returned False')
        self.assertEqual(list(df.columns.values), ['cpu_time', 'duration', 'num_procs'], 'wrong order of features returned by RCA')
        self.assertEqual(df.shape, (12,3), "wrong dataframe format")
        self.assertEqual([int(x) for x in list(df.loc['modified_z_score_ratio'])], [204, 27, 0], "wrong madz score ratios")



if __name__ == '__main__':
    unittest.main()
    #suite = unittest.TestLoader().loadTestsFromTestCase(TestStringMethods)
    #unittest.TextTestRunner(verbosity=2).run(suite)
