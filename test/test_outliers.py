#!/usr/bin/env python
from __future__ import print_function
import unittest
from sys import stderr, exit
from glob import glob
from os import environ
from json import loads

# put this above all epmt imports so they use defaults
environ['EPMT_USE_DEFAULT_SETTINGS'] = "1"

from epmtlib import set_logging
set_logging(-1)

# Put EPMT imports only after we have called set_logging()
import epmt_default_settings as settings

if environ.get('EPMT_USE_SQLALCHEMY'):
    settings.orm = 'sqlalchemy'
    settings.db_params = { 'url': 'sqlite:///:memory:', 'echo': False }
    if environ.get('EPMT_BULK_INSERT'):
        settings.bulk_insert = True

if environ.get('EPMT_USE_PG'):
    settings.db_params = { 'url': 'postgresql://postgres:example@localhost:5432/EPMT-TEST', 'echo': False } if (settings.orm == 'sqlalchemy') else {'provider': 'postgres', 'user': 'postgres','password': 'example','host': 'localhost', 'dbname': 'EPMT-TEST'}

from epmtlib import timing, frozen_dict
from orm import db_session, setup_db, Job
import epmt_query as eq
import epmt_outliers as eod
from epmt_cmds import epmt_submit


@timing
def setUpModule():
    setup_db(settings, drop=True)
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
        jobs = eq.get_jobs(tags='exp_name:linux_kernel', fmt='orm')
        (df, parts) = eod.detect_outlier_jobs(jobs)
        self.assertEqual(len(df[df.duration > 0]), 1)
        self.assertEqual(len(df[df.cpu_time > 0]), 1)
        self.assertEqual(len(df[df.num_procs > 0]), 0)
        self.assertTrue('outlier' in df[df.duration > 0]['jobid'].values[0], "wrong duration outlier")
        self.assertTrue('outlier' in df[df.cpu_time > 0]['jobid'].values[0], "wrong cpu_time outlier")
        self.assertEqual(len(parts), 3, "wrong number of items in partition dictionary")
        self.assertEqual(parts['duration'], (set([u'kern-6656-20190614-190245', u'kern-6656-20190614-194024', u'kern-6656-20190614-191138']), set([u'kern-6656-20190614-192044-outlier'])))

    @db_session
    def test_outlier_jobs_trained(self):
        all_jobs = eq.get_jobs(tags='exp_name:linux_kernel', fmt='orm')
        fltr = (~Job.jobid.like('%outlier%')) if settings.orm == 'sqlalchemy' else '"outlier" not in j.jobid'
        jobs_ex_outl = eq.get_jobs(tags='exp_name:linux_kernel', fmt='orm', fltr=fltr)
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
        all_jobs = eq.get_jobs(tags='exp_name:linux_kernel', fmt='orm')
        fltr = (~Job.jobid.like('%outlier%')) if settings.orm == 'sqlalchemy' else '"outlier" not in j.jobid'
        jobs_ex_outl = eq.get_jobs(tags='exp_name:linux_kernel', fmt='orm', fltr=fltr)
        r = eq.create_refmodel(jobs_ex_outl, fmt='terse', op_tags='*')
        features = ['rssmax', 'cpu_time', 'duration', 'num_procs']
        (df, parts, scores_df, sorted_tags, sorted_features) = eod.detect_outlier_ops(all_jobs, trained_model=r, features=features)
        self.assertEqual(df.shape, (20,6))
        self.assertEqual(set(df[df.duration > 0]['jobid']), set([u'kern-6656-20190614-192044-outlier']))
        self.assertEqual(set(df[df.cpu_time > 0]['jobid']), set([u'kern-6656-20190614-192044-outlier']))
        self.assertEqual(set(df[df.num_procs > 0]['jobid']), set([]))
        df_cols = list(df.columns)
        self.assertEqual(len(sorted_features), len(features))
        # ensure feature order is right
        self.assertEqual(sorted_features, ['cpu_time', 'duration', 'rssmax', 'num_procs'])
        self.assertNotEqual(sorted_features, features)
        # ensure df has the right feature order
        self.assertEqual(df_cols[2:], sorted_features)
        # esnure scores_df has the right order
        self.assertEqual(list(scores_df.columns)[1:], sorted_features)

        # ensure tag importance order is correct
        self.assertEqual(sorted_tags, [{u'op_instance': u'5', u'op_sequence': u'5', u'op': u'clean'}, {u'op_instance': u'4', u'op_sequence': u'4', u'op': u'build'}, {u'op_instance': u'3', u'op_sequence': u'3', u'op': u'configure'}, {u'op_instance': u'2', u'op_sequence': u'2', u'op': u'extract'}, {u'op_instance': u'1', u'op_sequence': u'1', u'op': u'download'}])
        # check scores_df[tags] is ordered right
        self.assertEqual([loads(t) for t in list(scores_df['tags'])], sorted_tags)
        # check df[tags] is ordered right
        uniq_tags = []
        for t in list(df['tags']):
            if not t in uniq_tags: uniq_tags.append(t)
        self.assertEqual(uniq_tags, sorted_tags)

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
        jobs = eq.get_jobs(tags='exp_name:linux_kernel', fmt='orm')
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
        jobs = eq.get_jobs(tags='launch_id:6656', fmt='orm')
        self.assertEqual(jobs.count(), 4, "incorrect job count using tags")
        parts = eod.partition_jobs(jobs, fmt='terse')
        self.assertEqual(len(parts), 3, "incorrect count of items in partition dict")
        self.assertEqual(parts['cpu_time'], (set([u'kern-6656-20190614-190245', u'kern-6656-20190614-194024', u'kern-6656-20190614-191138']), set([u'kern-6656-20190614-192044-outlier'])))
        self.assertEqual(parts['duration'], (set([u'kern-6656-20190614-190245', u'kern-6656-20190614-194024', u'kern-6656-20190614-191138']), set([u'kern-6656-20190614-192044-outlier'])))
        self.assertEqual(parts['num_procs'], (set([u'kern-6656-20190614-190245', u'kern-6656-20190614-192044-outlier', u'kern-6656-20190614-194024', u'kern-6656-20190614-191138']), set([])))

    @db_session
    def test_partition_jobs_by_ops(self):
        jobs = eq.get_jobs(fmt='terse', tags='exp_name:linux_kernel')
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
        fltr = (~Job.jobid.like('%outlier%')) if settings.orm == 'sqlalchemy' else '"outlier" not in j.jobid'
        ref_jobs = eq.get_jobs(tags='exp_name:linux_kernel', fmt='orm', fltr=fltr)
        fltr2 = (Job.jobid.like('%outlier%')) if settings.orm == 'sqlalchemy' else '"outlier" in j.jobid'
        outlier_job = eq.get_jobs(tags='exp_name:linux_kernel', fltr=fltr2, fmt='orm')
        (res, df, sl) = eod.detect_rootcause(ref_jobs, outlier_job)
        self.assertTrue(res, 'detect_rootcause returned False')
        self.assertEqual(list(df.columns.values), ['cpu_time', 'duration', 'num_procs'], 'wrong order of features returned by RCA')
        self.assertEqual(df.shape, (12,3), "wrong dataframe format")
        self.assertEqual([int(x) for x in list(df.loc['modified_z_score_ratio'])], [204, 27, 0], "wrong madz score ratios")

    @db_session
    def test_rca_ops(self):
        fltr = (~Job.jobid.like('%outlier%')) if settings.orm == 'sqlalchemy' else '"outlier" not in j.jobid'
        ref_jobs = eq.get_jobs(tags='exp_name:linux_kernel', fmt='orm', fltr=fltr)
        fltr2 = (Job.jobid.like('%outlier%')) if settings.orm == 'sqlalchemy' else '"outlier" in j.jobid'
        outlier_job = eq.get_jobs(tags='exp_name:linux_kernel', fltr=fltr2, fmt='orm')
        (res, df, sl) = eod.detect_rootcause_op(ref_jobs, outlier_job, tag='op_sequence:4')
        self.assertTrue(res, 'detect_rootcause_op returned False')
        self.assertEqual(list(df.columns.values), ['cpu_time', 'duration', 'num_procs'], 'wrong order of features returned by RCA')
        self.assertEqual(df.shape, (12,3), "wrong dataframe format")
        self.assertEqual([int(x) for x in list(df.loc['modified_z_score_ratio'])], [379, 56, 0], "wrong madz score ratios")

    @db_session
    def test_trained_model(self):
        fltr = (~Job.jobid.like('%outlier%')) if settings.orm == 'sqlalchemy' else '"outlier" not in j.jobid'
        jobs = eq.get_jobs(tags='exp_name:linux_kernel', fmt='orm', fltr=fltr)
        self.assertEqual(jobs.count(), 3)
        r = eq.create_refmodel(jobs, tag='exp_name:linux_kernel_test')
        self.assertEqual(r['tags'], {'exp_name': 'linux_kernel_test'})
        rq = eq.get_refmodels(tag='exp_name:linux_kernel_test', fmt='orm')
        self.assertEqual(rq.count(), 1)
        r1 = rq.first()
        self.assertEqual(r1.id, r['id'])
        self.assertEqual(r1.tags, {'exp_name': 'linux_kernel_test'})
        self.assertFalse(r1.op_tags)
        # pony and sqlalchemy have slightly different outputs
        # in pony each value in modfied_z_score dictionary is a 
        # a tuple, while in sqlalchemy it's a list. So, we use 
        # assertIn to check if either match occurs
        self.assertIn(r1.computed, ({'modified_z_score': {'duration': (1.0287, 542680315.0, 14860060.0), 'cpu_time': (1.3207, 449914707.0, 444671.0), 'num_procs': (0.0, 10600.0, 0.0)}},{'modified_z_score': {'duration': [1.0287, 542680315.0, 14860060.0], 'cpu_time': [1.3207, 449914707.0, 444671.0], 'num_procs': [0.0, 10600.0, 0.0]}}))
        self.assertEqual(set([j.jobid for j in r1.jobs]), set([u'kern-6656-20190614-194024', u'kern-6656-20190614-191138', u'kern-6656-20190614-190245']))



if __name__ == '__main__':
    unittest.main()
