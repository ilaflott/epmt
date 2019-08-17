#!/usr/bin/env python
from __future__ import print_function
import unittest
from sys import stderr, exit
import sys
from glob import glob
from pony.orm import db_session
from models import db, Job, Process
from pony.orm.core import Query, QueryResult
import pandas as pd
import datetime

# put this above all epmt imports
from os import environ
environ['EPMT_USE_DEFAULT_SETTINGS'] = "1"
from epmtlib import set_logging
set_logging(-1)

# Put EPMT imports only after we have called set_logging()
import epmt_query as eq
from epmtlib import timing, isString, frozen_dict, str_dict
from epmt_job import setup_orm_db
from epmt_cmds import epmt_submit
import epmt_default_settings as settings


@timing
def setUpModule():
    if settings.db_params.get('filename') != ':memory:':
        print('db_params MUST use in-memory sqlite for testing', file=stderr)
        exit(1)
    setup_orm_db(settings, drop=True)
    print('\n' + str(settings.db_params))
    datafiles='test/data/query/*.tgz'
    print('setUpModdule: importing {0}'.format(datafiles))
    epmt_submit(sorted(glob(datafiles)), dry_run=False)
    

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
        self.assertEqual(jobs, [u'685016', u'685003', u'685000'], 'job ordering not in reverse order of submission')
        df = eq.get_jobs(fmt='pandas')
        self.assertEqual(df.shape, (3, 47), 'wrong jobs dataframe shape')
        df = eq.get_jobs('685016', fmt='pandas')
        self.assertEqual(df['jobid'][0], '685016', "cannot specify job as a single job id string")
        self.assertEqual(df.shape[0],1, "wrong selection of jobs when specified as a string")
        jobs = eq.get_jobs('685016, 685000', fmt='dict')
        self.assertEqual(len(jobs), 2, 'job count wrong when selected a comma-separated string')

    @db_session
    def test_jobs_advanced(self):
        jobs = eq.get_jobs(fmt='terse', limit=2, offset=1)
        self.assertEqual(jobs, [u'685003', u'685000'], 'job limit/offset not working')
        jobs = eq.get_jobs(fltr=lambda j: '685000' not in j.jobid, fmt='orm')
        self.assertEqual(len(jobs), 2, 'jobs orm query with filter option')
        jobs = eq.get_jobs(tag='exp_component:ocean_month_rho2_1x1deg', fmt='terse')
        self.assertEqual(len(jobs), 1, 'jobs query with tag option')
        jobs = eq.get_jobs(tag='', fmt='terse')
        self.assertEqual(len(jobs), 0, 'jobs query with empty tag option')
        jobs = eq.get_jobs(tag={}, fmt='terse')
        self.assertEqual(len(jobs), 0, 'jobs query with {} tag option')
        df = eq.get_jobs(order='desc(j.duration)', limit=1, fmt='pandas')
        self.assertEqual(df.shape[0], 1, 'job query with limit')
        self.assertEqual('685016', df.loc[0,'jobid'], "jobs dataframe query with order")
        jobs = eq.get_jobs(before=0, fmt='terse')
        self.assertEqual(jobs, [u'685016', u'685003', u'685000'])
        jobs = eq.get_jobs(after=0, fmt='terse')
        self.assertEqual(jobs, [])
        jobs = eq.get_jobs(before='06/15/2019 00:00', fmt='terse')
        self.assertEqual(jobs, [])
        jobs = eq.get_jobs(after='06/15/2019 00:00', fmt='terse')
        self.assertEqual(jobs, [u'685016', u'685003', u'685000'])
        jobs = eq.get_jobs(before=-30, fmt='terse')
        self.assertEqual(jobs, [u'685016', u'685003', u'685000'])
        jobs = eq.get_jobs(after=-30, fmt='terse')
        self.assertEqual(jobs, [])
        # hosts
        jobs = eq.get_jobs(hosts=[], fmt='terse')
        self.assertEqual(jobs, [u'685016', u'685003', u'685000'])
        jobs = eq.get_jobs(hosts=['pp208', 'pp212'], fmt='terse')
        self.assertEqual(jobs, [u'685003', u'685000'])
        jobs = eq.get_jobs(hosts=['pp208', 'pp209', 'pp212'], fmt='terse')
        self.assertEqual(jobs, [u'685003', u'685000'])
        jobs = eq.get_jobs(hosts=['pp208', 'pp313', 'pp212'], fmt='terse')
        self.assertEqual(jobs, [u'685016', u'685003', u'685000'])
        # when
        jobs = eq.get_jobs(when='06/15/2019 08:00', fmt='terse')
        self.assertEqual(jobs, [u'685016', u'685003', u'685000'])
        jobs = eq.get_jobs(when='06/15/2019 07:00', fmt='terse')
        self.assertEqual(jobs, [])
        jobs = eq.get_jobs(when='06/15/2019 09:00', fmt='terse')
        self.assertEqual(jobs, [u'685016', u'685003', u'685000'])
        jobs = eq.get_jobs(when='06/15/2019 10:00', fmt='terse')
        self.assertEqual(jobs, [])
        jobs = eq.get_jobs(when=Job['685003'], fmt='terse')
        self.assertEqual(jobs, [u'685016', u'685003', u'685000'])
        # hosts + when
        jobs = eq.get_jobs(hosts = 'pp208', when='06/15/2019 08:00', fmt='terse')
        self.assertEqual(jobs, [u'685000'])
        jobs = eq.get_jobs(hosts = 'pp208', when='06/15/2019 11:00', fmt='terse')
        self.assertEqual(jobs, [])
        jobs = eq.get_jobs(when='06/15/2019 08:00', hosts=['pp208', 'pp212'], fmt='terse')
        self.assertEqual(jobs, [u'685003', u'685000'])
        jobs = eq.get_jobs(when='06/16/2019 08:00', hosts=['pp208', 'pp212'], fmt='terse')
        self.assertEqual(jobs, [])

    @db_session
    def conv_jobs(self):
        for fmt in ['dict', 'terse', 'pandas', 'orm']:
            jobs = eq.get_jobs(['685000', '685003'], fmt=fmt)
            self.assertEqual(eq.conv_jobs(jobs, fmt='terse'), ['685000', '685003'])
            self.assertEqual(eq.conv_jobs(jobs, fmt='orm')[:], [Job[u'685000'], Job[u'685003']])
            self.assertEqual(list(eq.conv_jobs(jobs, fmt='pandas')['jobid'].values), [u'685000', u'685003'])
            self.assertEqual([j['jobid'] for j in eq.conv_jobs(jobs, fmt='dict')], ['685000', '685003'])


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

        df = eq.get_procs(limit=5, order='desc(p.cpu_time)', fmt='pandas')
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
        # hosts, when
        procs = eq.get_procs('685000', when=datetime.datetime(2019, 6, 15, 11, 53), fmt='terse')
        pids = [Process[p].pid for p in procs]
        self.assertEqual(pids, [6098, 6226])
        procs = eq.get_procs('685000', when='06/15/2019 11:53', fmt='terse')
        pids = [Process[p].pid for p in procs]
        self.assertEqual(pids, [6098, 6226])
        self.assertEqual(eq.get_procs('685000', hosts=['pp208'], fmt='orm').count(), 3480)
        self.assertEqual(eq.get_procs('685000', hosts=['pp208', 'pp209'], fmt='orm').count(), 3480)
        self.assertEqual(eq.get_procs('685000', hosts=['pp209'], fmt='orm').count(), 0)
        self.assertEqual(eq.get_procs(['685000', '685003'], hosts=['pp208', 'pp212'], fmt='orm').count(), 
7265)
        self.assertEqual(eq.get_procs(['685000', '685003'], hosts=['pp212'], fmt='orm').count(), 3785)


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
                    self.assertIn(type(out), [Query, QueryResult],'output format not ORM when input fmt: {0}'.format(inp_fmt))
                    self.assertEqual(sorted([j.jobid for j in out]), sorted(ref), 'error in {0} -> {1}'.format(inp_fmt, out_fmt))
                elif out_fmt == 'dict':
                    self.assertTrue((type(out) == list) and (type(out[0]) == dict),'output format not dictlist when input fmt: {0}'.format(inp_fmt))
                    self.assertEqual(sorted([j['jobid'] for j in out]), sorted(ref), 'error in {0} -> {1}'.format(inp_fmt, out_fmt))
                elif out_fmt == 'pandas':
                    self.assertEqual(type(out), pd.DataFrame,'output format not dataframe when input fmt: {0}'.format(inp_fmt))
                    self.assertEqual(sorted(list(out['jobid'].values)), sorted(ref), 'error in {0} -> {1}'.format(inp_fmt, out_fmt))

    @db_session
    def test_job_proc_tags(self):
        tags = eq.job_proc_tags(['685000', '685016'], fold=False)
        self.assertEqual(len(tags), 89, "wrong unique process tags count")
        tags = [ str_dict(d) for d in tags ]
        from hashlib import md5
        self.assertEqual(md5(str(tags).encode('utf-8')).hexdigest(), 'bd7eabf266aa5b179bbe4d65b35bd47f', 'wrong hash for job_proc_tags')

    @db_session
    def test_op_metrics(self):
        df = eq.op_metrics(['685000', '685016'])
        self.assertEqual(df.shape, (178,32), "wrong dataframe shape for op_metrics")
        top = df[['job', 'tags', 'duration']].sort_values('duration', axis=0, ascending=False)[:1]
        self.assertEqual(top.tags.values[0], {u'op_instance': u'2', u'op_sequence': u'89', u'op': u'dmput'})
        self.assertEqual(int(top.duration.values[0]), 7008334182)
        df = eq.op_metrics(['685000', '685016'], tags='op_sequence:89')
        self.assertEqual([int(f) for f in list(df.duration.values)], [6463542235, 7008334182])

        df = eq.op_metrics(['685000', '685003', '685016'])
        self.assertEqual(df.shape,(573,32), 'wrong op_metrics shape when no tag specified')
        #self.assertEqual([int(x) for x in df.duration.values][:10], [277371, 3607753, 95947, 3683612, 114, 94, 4087414, 362007, 367143, 29337], 'wrong op_metrics when no tag specified')
        self.assertEqual([int(x) for x in df.duration.values][:10], [6598692, 6709043, 6707903, 6676748, 6939098, 6541841, 6788901, 6125293, 6427261, 6472072], 'wrong op_metrics when no tag specified')

        df = eq.op_metrics(['685000', '685003', '685016'], tags=['op:hsmget', 'op:mv'])
        self.assertEqual(df.shape, (6,32), 'wrong op_metrics shape with tags specified')
        self.assertEqual(list(df.duration.values), [18116213243, 6688820532, 7585973173, 25706545, 212902301, 62601798])
        self.assertEqual(list(df.tags.values), [{'op': 'hsmget'}, {'op': 'hsmget'}, {'op': 'hsmget'}, {'op': 'mv'}, {'op': 'mv'}, {'op': 'mv'}])

    @db_session
    def test_op_metrics_grouped(self):
        #from hashlib import md5
        df = eq.op_metrics(['685000', '685003', '685016'], group_by_tag=True)
        self.assertEqual(df.shape,(459,30), 'wrong op_metrics grouped shape when no tag specified')
        self.assertEqual(list(df['tags'].values[:10]), [{u'op_instance': u'11', u'op_sequence': u'66', u'op': u'cp'}, {u'op_instance': u'15', u'op_sequence': u'79', u'op': u'cp'}, {u'op_instance': u'3', u'op_sequence': u'247', u'op': u'cp'}, {u'op_instance': u'3', u'op_sequence': u'251', u'op': u'cp'}, {u'op_instance': u'3', u'op_sequence': u'255', u'op': u'cp'}, {u'op_instance': u'3', u'op_sequence': u'259', u'op': u'cp'}, {u'op_instance': u'3', u'op_sequence': u'263', u'op': u'cp'}, {u'op_instance': u'3', u'op_sequence': u'267', u'op': u'cp'}, {u'op_instance': u'3', u'op_sequence': u'271', u'op': u'cp'}, {u'op_instance': u'3', u'op_sequence': u'30', u'op': u'cp'}], 'wrong tags ordering in grouped op_metrics')
        self.assertEqual([int(x) for x in df.duration.values][:10], [13307735, 13384651, 3699824, 3679446, 3683612, 3689543, 3702057, 3735581, 3709788, 13480939], 'wrong duration values in grouped op_metrics')

        df = eq.op_metrics(['685000', '685003', '685016'], tags=['op:hsmget', 'op:mv'], group_by_tag=True)
        self.assertEqual(df.shape, (2,30), 'wrong op_metrics shape with tags specified')
        self.assertEqual(list(df.tags.values), [{u'op': u'hsmget'}, {u'op': u'mv'}])
        self.assertEqual(list(df['cpu_time'].values), [208577324.0, 30292583.0])

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
    def test_op_roots(self):
        op_root_procs = eq.op_roots(['685000', '685003', '685016'], 'op_sequence:1', fmt='orm')
        l = eq.select((p.job.jobid, p.pid) for p in op_root_procs)[:]
        self.assertEqual(l, [(u'685000', 6226), (u'685000', 10042), (u'685000', 10046), (u'685000', 10058), (u'685000', 10065), (u'685000', 10066), (u'685003', 29079), (u'685003', 31184), (u'685003', 31185), (u'685003', 31191), (u'685003', 31198), (u'685003', 31199), (u'685016', 122259), (u'685016', 128848), (u'685016', 128849), (u'685016', 128855), (u'685016', 128862), (u'685016', 128863)])
        df = eq.op_roots(['685000', '685003', '685016'], 'op_sequence:1', fmt='pandas')
        self.assertEqual(df.shape, (18,50))
        self.assertEqual(list(df['pid'].values), [6226, 10042, 10046, 10058, 10065, 10066, 29079, 31184, 31185, 31191, 31198, 31199, 122259, 128848, 128849, 128855, 128862, 128863])

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

    @db_session
    def test_refmodel_crud(self):
        jobs = eq.get_jobs(fmt='terse')
        self.assertEqual(len(jobs), 3)
        model_name = 'test_model'
        r = eq.create_refmodel(jobs, tag='model_name:'+model_name)
        self.assertEqual(r['tags'], {'model_name': model_name})
        rq = eq.get_refmodels(tag='model_name:'+model_name, fmt='orm')
        self.assertEqual(rq.count(), 1)
        r1 = rq.first()
        self.assertEqual(r1.id, r['id'])
        self.assertEqual(r1.tags, {'model_name': model_name})
        self.assertFalse(r1.op_tags)
        self.assertEqual(set(r1.jobs.jobid), set(jobs))
        n = eq.delete_refmodels(r['id'])
        self.assertEqual(n, 1, 'wrong ref_model delete count')

    @db_session
    def test_dm_calc(self):
        jobs = eq.get_jobs(['685000', '685003', '685016'], fmt='orm')
        self.assertEqual(jobs.count(), 3)
        (perc, df, j_cpu) = eq.dm_calc(jobs)
        self.assertEqual(perc, 43.16, 'wrong dm percent')
        self.assertEqual(df.shape, (6, 30), 'wrong df shape')
        self.assertEqual(df['cpu_time'].sum(), 273510353.0, 'wrong dm cpu time sum')
        self.assertEqual(j_cpu, 633756327.0, 'wrong job cpu time sum')

    @db_session
    def test_dm_calc_iter(self):
        jobs = eq.get_jobs(['685000', '685003', '685016'], fmt='orm')
        self.assertEqual(jobs.count(), 3)
        (dm_percent, df, all_jobs_cpu_time, agg_df) = eq.dm_calc_iter(jobs) 
        self.assertEqual(dm_percent, 43.157, 'wrong dm percent')
        self.assertEqual(df.shape, (17, 31))
        self.assertEqual(all_jobs_cpu_time, 633756327.0, 'wrong job cpu time sum')
        self.assertEqual(agg_df.shape, (3, 4))
        self.assertEqual(list(agg_df['dm_cpu_time'].values), [69603181.0, 61358737.0, 142548435.0])
        self.assertEqual(list(agg_df['dm_cpu_time%'].values), [62.0, 66.0, 33])
        self.assertEqual(list(agg_df['jobid'].values), ['685000', '685003', '685016'])
        self.assertEqual(list(agg_df['job_cpu_time'].values), [113135329.0, 93538033.0, 427082965.0])

    @db_session
    def test_zz_delete_jobs(self):
        #with self.assertRaises(EnvironmentError):
        #    eq.delete_jobs('685000')
        #settings.allow_job_deletion = True
        n = eq.delete_jobs(['685000', '685016'])
        self.assertEqual(n, 0, 'multiple jobs deleted without "force"')

        # test before/after
        j = eq.get_jobs(fmt='orm')[:][-1]
        ndays = (datetime.datetime.now() - j.start).days 
        n = eq.delete_jobs([], force=True, after=-ndays)
        self.assertEqual(n, 0)
        n = eq.delete_jobs([], force=True, after='06/16/2019 00:00')
        self.assertEqual(n, 0)
        n = eq.delete_jobs([], force=True, before='06/15/2019 00:00')
        self.assertEqual(n, 0)

        n = eq.delete_jobs(['685000', '685016'], force=True)
        self.assertEqual(n, 2, 'jobs not deleted even with "force"')

        n = eq.delete_jobs([], force=True, before=-(ndays-1))
        self.assertEqual(n, 1)


if __name__ == '__main__':
    unittest.main()
    #suite = unittest.TestLoader().loadTestsFromTestCase(QueryAPI)
    #unittest.TextTestRunner(verbosity=2).run(suite)
