#!/usr/bin/env python
from __future__ import print_function
import unittest
from sys import stderr, exit
from glob import glob
from os import environ
from pony.orm import db_session
from models import db
from json import loads

# put this above all epmt imports so they use defaults
environ['EPMT_USE_DEFAULT_SETTINGS'] = "1"

from epmtlib import set_logging
set_logging(-1)

# Put EPMT imports only after we have called set_logging()
import epmt_query as eq
import epmt_outliers as eod
from epmtlib import timing, frozen_dict
from epmt_cmds import epmt_submit
from epmt_job import setup_orm_db
import epmt_default_settings as settings

@timing
def setUpModule():
    if settings.db_params.get('filename') != ':memory:':
        print('db_params MUST use in-memory sqlite for testing', file=stderr)
        exit(1)
    setup_orm_db(settings, drop=True)
    print('\n' + str(settings.db_params))
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
        self.assertTrue('outlier' in df[df.cpu_time > 0]['jobid'].values[0], "wrong cpu_time outlier")
        self.assertEqual(len(parts), 3, "wrong number of items in partition dictionary")
        self.assertEqual(parts['duration'], (set([u'kern-6656-20190614-190245', u'kern-6656-20190614-194024', u'kern-6656-20190614-191138']), set([u'kern-6656-20190614-192044-outlier'])))

    @db_session
    def test_outlier_jobs_trained(self):
        all_jobs = eq.get_jobs(tag='exp_name:linux_kernel', fmt='orm')
        jobs_ex_outl = eq.get_jobs(tag='exp_name:linux_kernel', fmt='orm', fltr='"outlier" not in j.jobid')
        r = eq.create_refmodel(jobs_ex_outl, fmt='terse')
        (df, parts) = eod.detect_outlier_jobs(all_jobs, trained_model=r)
        self.assertEqual(len(df[df.duration > 0]), 1, "incorrect count of duration outliers")
        self.assertEqual(len(df[df.cpu_time > 0]), 1, "incorrect count of cpu_time outliers")
        self.assertEqual(len(df[df.num_procs > 0]), 0, "incorrect count of num_procs outliers")
        self.assertTrue('outlier' in df[df.duration > 0]['jobid'].values[0], "wrong duration outlier")
        self.assertTrue('outlier' in df[df.cpu_time > 0]['jobid'].values[0], "wrong cpu_time outlier")
        self.assertEqual(parts['duration'], (set([u'kern-6656-20190614-190245', u'kern-6656-20190614-194024', u'kern-6656-20190614-191138']), set([u'kern-6656-20190614-192044-outlier'])))
        # now create a ref model that *includes* the outlier job
        # this way it won't later be classified as a outlier
        r = eq.create_refmodel(all_jobs, fmt='terse')
        (df, parts) = eod.detect_outlier_jobs(all_jobs, trained_model=r)
        # check there are no outliers
        self.assertEqual(len(df[df.duration > 0]), 0, "incorrect count of duration outliers")
        self.assertEqual(len(df[df.cpu_time > 0]), 0, "incorrect count of cpu_time outliers")
        self.assertEqual(len(df[df.num_procs > 0]), 0, "incorrect count of num_procs outliers")

    @db_session
    def test_outlier_ops_trained(self):
        all_jobs = eq.get_jobs(tag='exp_name:linux_kernel', fmt='orm')
        jobs_ex_outl = eq.get_jobs(tag='exp_name:linux_kernel', fmt='orm', fltr='"outlier" not in j.jobid')
        r = eq.create_refmodel(jobs_ex_outl, fmt='terse', op_tags='*')
        (df, parts, _, _ , _) = eod.detect_outlier_ops(all_jobs, trained_model=r)
        self.assertEqual(df.shape, (20,5))
        self.assertEqual(set(df[df.duration > 0]['jobid']), set([u'kern-6656-20190614-192044-outlier']))
        self.assertEqual(set(df[df.cpu_time > 0]['jobid']), set([u'kern-6656-20190614-192044-outlier']))
        self.assertEqual(set(df[df.num_procs > 0]['jobid']), set([]))
        parts = { frozen_dict(loads(k)): v for k,v in parts.items() }
        self.assertEqual(parts[frozen_dict({"op_instance": "4", "op_sequence": "4", "op": "build"})], (set([u'kern-6656-20190614-194024', u'kern-6656-20190614-190245', u'kern-6656-20190614-191138']), set([u'kern-6656-20190614-192044-outlier'])))

        # now also use the outlier job while creating the refmodel
        # this way, there should be NO outlier ops
        r = eq.create_refmodel(all_jobs, fmt='terse', op_tags='*')
        (df, parts, _, _ , _) = eod.detect_outlier_ops(all_jobs, trained_model=r)
        self.assertEqual(len(df.query('duration > 0 | cpu_time > 0 | num_procs > 0')), 0)

        # now let's try creating a refmodel with a specific op_tag
        # we will get a warning in this test as the full jobs set has a different
        # set of unique process tags than the ref jobs set
        r = eq.create_refmodel(jobs_ex_outl, fmt='terse', op_tags='op_instance:4;op_sequence:4;op:build')
        (df, parts, _, _ , _) = eod.detect_outlier_ops(all_jobs, trained_model=r)
        self.assertEqual(df.shape, (4,5))
        self.assertEqual(len(parts), 1)
        parts = { frozen_dict(loads(k)): v for k,v in parts.items() }
        self.assertEqual(parts[frozen_dict({"op_instance": "4", "op_sequence": "4", "op": "build"})], (set([u'kern-6656-20190614-194024', u'kern-6656-20190614-190245', u'kern-6656-20190614-191138']), set([u'kern-6656-20190614-192044-outlier'])))

    @db_session
    def test_outlier_ops(self):
        jobs = eq.get_jobs(tag='exp_name:linux_kernel', fmt='orm')
        (df, parts, _, _, _) = eod.detect_outlier_ops(jobs)
        self.assertEqual(df.shape, (20,5), "wrong shape of df from detect_outlier_ops")
        self.assertEqual(len(df[df.duration > 0]), 3, 'wrong outlier count for duration')
        self.assertEqual(len(df[df.cpu_time > 0]), 5, 'wrong outlier count for cpu_time')
        self.assertEqual(len(df[df.num_procs > 0]), 0, 'wrong outlier count for num_procs')
        self.assertEqual(list(df.loc[2].values), [u'kern-6656-20190614-192044-outlier', {u'op_instance': u'4', u'op_sequence': u'4', u'op': u'build'}, 1, 1, 0])
        self.assertEqual(len(parts), 5, 'wrong number of distinct tags')
        #print(parts.keys())
        parts = { frozen_dict(loads(k)): v for k,v in parts.items() }
        self.assertEqual(parts[frozen_dict({"op_instance": "4", "op_sequence": "4", "op": "build"})], (set([u'kern-6656-20190614-190245', u'kern-6656-20190614-191138', u'kern-6656-20190614-194024']), set([u'kern-6656-20190614-192044-outlier'])))

        (df, parts, _, _, _) = eod.detect_outlier_ops(jobs, tags = {"op_instance": "4", "op_sequence": "4", "op": "build"})
        self.assertEqual(df.shape, (4,5), "wrong shape of df from detect_outlier_ops with supplied tag")
        self.assertEqual(list(df.duration), [0, 0, 1, 0])
        self.assertEqual(list(df.cpu_time), [0, 0, 1, 0])
        self.assertEqual(list(df.num_procs), [0, 0, 0, 0])
        self.assertEqual(len(parts), 1)
        parts = { frozen_dict(loads(k)): v for k,v in parts.items() }
        self.assertEqual(parts[frozen_dict({"op_instance": "4", "op_sequence": "4", "op": "build"})], (set([u'kern-6656-20190614-190245', u'kern-6656-20190614-191138', u'kern-6656-20190614-194024']), set([u'kern-6656-20190614-192044-outlier'])))


    @db_session
    def test_partition_jobs(self):
        jobs = eq.get_jobs(tag='launch_id:6656', fmt='orm')
        self.assertEqual(len(jobs), 4, "incorrect job count using tags")
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
        parts = { frozen_dict(loads(k)): v for k,v in parts.items() }
        self.assertEqual(parts[frozen_dict({"op_instance": "3", "op_sequence": "3", "op": "configure"})], (set([u'kern-6656-20190614-190245', u'kern-6656-20190614-191138', u'kern-6656-20190614-194024']), set([u'kern-6656-20190614-192044-outlier'])), "wrong partitioning for configure op")
        parts = eod.partition_jobs_by_ops(jobs, tags = 'op:build;op_instance:4;op_sequence:4')
        self.assertEqual(len(parts), 1)
        parts = { frozen_dict(loads(k)): v for k,v in parts.items() }
        self.assertEqual(parts[frozen_dict({"op_instance": "4", "op_sequence": "4", "op": "build"})], (set([u'kern-6656-20190614-190245', u'kern-6656-20190614-191138', u'kern-6656-20190614-194024']), set([u'kern-6656-20190614-192044-outlier'])), "wrong partitioning when supplying a single tag string")
        parts = eod.partition_jobs_by_ops(jobs, tags = ['op:build;op_instance:4;op_sequence:4', {"op_instance": "2", "op_sequence": "2", "op": "extract"}])
        self.assertEqual(len(parts), 2)
        parts = { frozen_dict(loads(k)): v for k,v in parts.items() }
        self.assertEqual(parts[frozen_dict({"op_instance": "4", "op_sequence": "4", "op": "build"})], (set([u'kern-6656-20190614-190245', u'kern-6656-20190614-191138', u'kern-6656-20190614-194024']), set([u'kern-6656-20190614-192044-outlier'])))
        self.assertEqual(parts[frozen_dict({"op_instance": "2", "op_sequence": "2", "op": "extract"})], (set([u'kern-6656-20190614-190245', u'kern-6656-20190614-191138', u'kern-6656-20190614-194024']), set([u'kern-6656-20190614-192044-outlier'])), "wrong partitioning when supplying tags consisting of a list of string and dict")
        

    @db_session
    def test_rca_jobs(self):
        ref_jobs = eq.get_jobs(tag='exp_name:linux_kernel', fltr='"outlier" not in j.jobid', fmt='orm')
        outlier_job = eq.get_jobs(tag='exp_name:linux_kernel', fltr='"outlier" in j.jobid', fmt='orm')
        (res, df, sl) = eod.detect_rootcause(ref_jobs, outlier_job)
        self.assertTrue(res, 'detect_rootcause returned False')
        self.assertEqual(list(df.columns.values), ['cpu_time', 'duration', 'num_procs'], 'wrong order of features returned by RCA')
        self.assertEqual(df.shape, (12,3), "wrong dataframe format")
        self.assertEqual([int(x) for x in list(df.loc['modified_z_score_ratio'])], [204, 27, 0], "wrong madz score ratios")

    @db_session
    def test_rca_ops(self):
        ref_jobs = eq.get_jobs(tag='exp_name:linux_kernel', fltr='"outlier" not in j.jobid', fmt='orm')
        outlier_job = eq.get_jobs(tag='exp_name:linux_kernel', fltr='"outlier" in j.jobid', fmt='orm')
        (res, df, sl) = eod.detect_rootcause_op(ref_jobs, outlier_job, tag='op_sequence:4')
        self.assertTrue(res, 'detect_rootcause_op returned False')
        self.assertEqual(list(df.columns.values), ['cpu_time', 'duration', 'num_procs'], 'wrong order of features returned by RCA')
        self.assertEqual(df.shape, (12,3), "wrong dataframe format")
        self.assertEqual([int(x) for x in list(df.loc['modified_z_score_ratio'])], [379, 56, 0], "wrong madz score ratios")

    @db_session
    def test_trained_model(self):
        jobs = eq.get_jobs(tag='exp_name:linux_kernel', fltr='"outlier" not in j.jobid', fmt='terse')
        self.assertEqual(len(jobs), 3)
        r = eq.create_refmodel(jobs, tag='exp_name:linux_kernel_test')
        self.assertEqual(r['tags'], {'exp_name': 'linux_kernel_test'})
        rq = eq.get_refmodels(tag='exp_name:linux_kernel_test', fmt='orm')
        self.assertEqual(rq.count(), 1)
        r1 = rq.first()
        self.assertEqual(r1.id, r['id'])
        self.assertEqual(r1.tags, {'exp_name': 'linux_kernel_test'})
        self.assertFalse(r1.op_tags)
        self.assertEqual(r1.computed, {'modified_z_score': {'duration': (1.0287, 542680315.0, 14860060.0), 'cpu_time': (1.3207, 449914707.0, 444671.0), 'num_procs': (0.0, 10600.0, 0.0)}})
        self.assertEqual(set(r1.jobs.jobid), set([u'kern-6656-20190614-194024', u'kern-6656-20190614-191138', u'kern-6656-20190614-190245']))



if __name__ == '__main__':
    unittest.main()
    #suite = unittest.TestLoader().loadTestsFromTestCase(TestStringMethods)
    #unittest.TextTestRunner(verbosity=2).run(suite)