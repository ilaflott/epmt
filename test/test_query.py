#!/usr/bin/env python
from __future__ import print_function
import unittest
from sys import stderr, exit
from glob import glob
from pony.orm import db_session
from models import db
from pony.orm.core import Query
import pandas as pd
import datetime

# put this above all epmt imports so they use defaults
from os import environ
environ['EPMT_USE_DEFAULT_SETTINGS'] = "1"

from epmtlib import set_logging, timing
set_logging(-1)

import epmt_query as eq
from epmt_job import setup_orm_db
from epmt_cmds import epmt_submit
import epmt_default_settings as settings


@timing
def setUpModule():
    if settings.db_params.get('filename') != ':memory:':
        print('db_params MUST use in-memory sqlite for testing', file=stderr)
        exit(1)
    setup_orm_db(settings, drop=True)
    datafiles='test/data/query/*.tgz'
    print('\nsetUpModdule: importing {0}'.format(datafiles))
    epmt_submit(glob(datafiles), dry_run=False)
    

def tearDownModule():
    pass

class QueryAPI(unittest.TestCase):
#     # called ONCE before before first test in this class starts
#     @classmethod
#     def setUpClass(cls):
#         pass
# 
#     # called ONCE after last tests in this class is finished
#     @classmethod
#     def tearDownClass(cls):
#         pass
# 
#     # called before every test
#     def setUp(self):
#         pass
# 
#     # called after every test
#     def tearDown(self):
#         pass

    def test_jobs(self):
        jobs = eq.get_jobs(fmt='terse')
        self.assertEqual(type(jobs), list, 'wrong jobs format with terse')
        self.assertEqual(len(jobs), 3, 'job count in db wrong')
        df = eq.get_jobs(fmt='pandas')
        self.assertEqual(df.shape, (3, 47), 'wrong jobs dataframe shape')
        df = eq.get_jobs('685016', fmt='pandas')
        self.assertEqual(df['jobid'][0], '685016', "cannot specify job as a single job id string")
        self.assertEqual(df.shape[0],1, "wrong selection of jobs when specified as a string")
        jobs = eq.get_jobs('685016, 685000', fmt='dict')
        self.assertEqual(len(jobs), 2, 'job count wrong when selected a comma-separated string')

    @db_session
    def test_jobs_advanced(self):
        jobs = eq.get_jobs(fltr=lambda j: '685000' not in j.jobid, fmt='orm')
        self.assertEqual(jobs.count(), 2, 'jobs orm query with filter option')
        jobs = eq.get_jobs(tag='exp_component:ocean_month_rho2_1x1deg', fmt='terse')
        self.assertEqual(len(jobs), 1, 'jobs query with tag option')
        jobs = eq.get_jobs(tag='', fmt='terse')
        self.assertEqual(len(jobs), 0, 'jobs query with empty tag option')
        jobs = eq.get_jobs(tag={}, fmt='terse')
        self.assertEqual(len(jobs), 0, 'jobs query with {} tag option')
        df = eq.get_jobs(order='desc(j.duration)', limit=1, fmt='pandas')
        self.assertEqual(df.shape[0], 1, 'job query with limit')
        self.assertEqual('685016', df.loc[0,'jobid'], "jobs dataframe query with order")

    @db_session
    def test_procs(self):
        procs = eq.get_procs(['685016'], fmt='terse')
        self.assertEqual(type(procs), list, 'wrong procs format with terse')
        self.assertEqual(len(procs), 3412, 'wrong count of processes in terse')
        procs = eq.get_procs(['685016', '685000'], fmt='orm')
        self.assertEqual(len(procs), 6892, 'wrong count of processes in ORM format')
        df = eq.get_procs(fmt='pandas', limit=10)
        self.assertEqual(df.shape, (10,50), "incorrect dataframe shape with limit")

    @db_session
    def test_procs_advanced(self):
        procs = eq.get_procs(fltr=lambda p: p.duration > 1000000, order='desc(p.duration)', fmt='orm')
        self.assertEqual(len(procs), 630, 'wrong count of processes in ORM format using filter')
        self.assertEqual(int(procs.first().duration), 7005558348, 'wrong order when using orm with filter and order')

        df = eq.get_procs(limit=5, order='desc(p.exclusive_cpu_time)', fmt='pandas')
        self.assertEqual(df.shape, (5,50), "incorrect dataframe shape")
        self.assertEqual('685016', df.loc[0,'job'], "ordering of processes wrong in dataframe")

        # empty tag query
        procs = eq.get_procs(tag='', fmt='terse')
        self.assertEqual(len(procs), 0, 'procs query with empty tag option')
        procs = eq.get_jobs(tag={}, fmt='terse')
        self.assertEqual(len(procs), 0, 'procs query with {} tag option')

        procs_with_tag = eq.get_procs(tag='op_sequence:4', fltr='p.duration > 10000000', order='desc(p.duration)', fmt='orm')
        self.assertEqual(len(procs_with_tag), 2, 'incorrect process count when using tag and filter')
        p = procs_with_tag.first()
        self.assertEqual(int(p.duration), 207384313, 'wrong duration or order when used with tag and filter')
        self.assertEqual(p.descendants.count(), 85, 'wrong descendant count or order when used with tag and filter')

    @db_session
    def test_jobs_conv(self):
        ref = eq.get_jobs(fmt='terse')
        for inp_fmt in ['terse','orm','pandas','dict']:
            jobs = eq.get_jobs(fmt=inp_fmt)
            for out_fmt in ['pandas', 'terse', 'orm', 'dict']:
                out = eq.conv_jobs(jobs, fmt=out_fmt)
                if out_fmt == 'terse':
                    self.assertEqual(type(out), list,'output format not terse when input fmt: {0}'.format(inp_fmt))
                    self.assertEqual(sorted(out), sorted(ref), 'error in {0} -> {1}'.format(inp_fmt, out_fmt))
                elif out_fmt == 'orm':
                    self.assertEqual(type(out), Query,'output format not ORM when input fmt: {0}'.format(inp_fmt))
                    self.assertEqual(sorted([j.jobid for j in out]), sorted(ref), 'error in {0} -> {1}'.format(inp_fmt, out_fmt))
                elif out_fmt == 'dict':
                    self.assertTrue((type(out) == list) and (type(out[0]) == dict),'output format not dictlist when input fmt: {0}'.format(inp_fmt))
                    self.assertEqual(sorted([j['jobid'] for j in out]), sorted(ref), 'error in {0} -> {1}'.format(inp_fmt, out_fmt))
                elif out_fmt == 'pandas':
                    self.assertEqual(type(out), pd.DataFrame,'output format not dataframe when input fmt: {0}'.format(inp_fmt))
                    self.assertEqual(sorted(list(out['jobid'].values)), sorted(ref), 'error in {0} -> {1}'.format(inp_fmt, out_fmt))

    @db_session
    def test_unique_proc_tags(self):
        tags = eq.job_proc_tags(['685000', '685016'], fold=False)
        self.assertEqual(len(tags), 89, "wrong unique process tags count")
        from hashlib import md5
        self.assertEqual(md5(str(sorted(tags))).hexdigest(), '7083bed0954830e2daa34a1113209177', 'wrong hash of tags')

    @db_session
    def test_op_metrics(self):
        df = eq.op_metrics(['685000', '685016'])
        self.assertEqual(df.shape, (178,33), "wrong dataframe shape for op_metrics")
        top = df[['job', 'tags', 'duration']].sort_values('duration', axis=0, ascending=False)[:1]
        self.assertEqual(top.tags.values[0], {u'op_instance': u'2', u'op_sequence': u'89', u'op': u'dmput'})
        self.assertEqual(int(top.duration.values[0]), 7008334182)
        df = eq.op_metrics(['685000', '685016'], tags='op_sequence:89')
        self.assertEqual([int(f) for f in list(df.duration.values)], [6463542235, 7008334182])

    @db_session
    def test_root(self):
        p = eq.root('685016')
        self.assertEqual((p['pid'], p['exename']), (122181, u'tcsh'))
        p = eq.root('685016', fmt='orm')
        self.assertEqual(p.pid, 122181)
        df = eq.root('685016', fmt='pandas')
        self.assertEqual(df.shape, (1,50))
        self.assertEqual(df.loc[0,'pid'], 122181)

    @db_session
    def test_timeline(self):
        jobs = eq.get_jobs(fmt='orm')
        procs = eq.timeline(jobs, fmt='orm')
        p1 = procs.first()
        self.assertEqual(p1.start, min(min(j.processes.start) for j in jobs))
        self.assertEqual([ p.start for p in procs[:3] ], [datetime.datetime(2019, 6, 15, 11, 52, 4, 126892), datetime.datetime(2019, 6, 15, 11, 52, 4, 133795), datetime.datetime(2019, 6, 15, 11, 52, 4, 142141)])
        procs = eq.timeline('685016', fmt='orm', limit=5)
        pids = [p.pid for p in procs]
        self.assertEqual(pids, [122181, 122182, 122183, 122184, 122185])

    def test_zz_delete_jobs(self):
        with self.assertRaises(EnvironmentError):
            eq.delete_jobs('685000')
        settings.allow_job_deletion = True
        n = eq.delete_jobs(['685000', '685016'])
        self.assertEqual(n, 0, 'multiple jobs deleted without "force"')
        n = eq.delete_jobs(['685000', '685016'], force=True)
        self.assertEqual(n, 2, 'jobs not deleted even with "force"')


if __name__ == '__main__':
    unittest.main()
    #suite = unittest.TestLoader().loadTestsFromTestCase(QueryAPI)
    #unittest.TextTestRunner(verbosity=2).run(suite)
