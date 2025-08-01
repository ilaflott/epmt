#!/usr/bin/env python

# the import below is crucial to get a sane test environment
import unittest
from datetime import datetime
from glob import glob
from epmt.orm import Job, Operation, Process, db_session, setup_db
from epmt.orm.sqlalchemy.general import orm_get, orm_commit
from epmt.epmtlib import capture, timing, epmt_logging_init, str_dict
from epmt.epmt_cmds import epmt_submit
import epmt.epmt_query as eq
import epmt.epmt_settings as settings
from . import install_root
epmt_logging_init(0)
JOBS_LIST = ['685016', '685003', '685000']


def do_cleanup():
    eq.delete_jobs(JOBS_LIST, force=True, remove_models=True)


@timing
def setUpModule():
    #    print('\n' + str(settings.db_params))
    setup_db(settings)
    do_cleanup()
    datafiles = '{}/test/data/query/*.tgz'.format(install_root)
    #    print('setUpModdule: importing {0}'.format(datafiles))
    with capture() as (out, err):
        epmt_submit(sorted(glob(datafiles)), dry_run=False)
    # only use modz as the tests are written that way
    settings.univariate_classifiers = ['modified_z_score']


def tearDownModule():
    do_cleanup()


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

    def test_get_features(self):
        f = eq.get_features(['685000', '685003', '685016'])
        self.assertTrue(set(f) >= set(['PERF_COUNT_SW_CPU_CLOCK',
                                       'cancelled_write_bytes',
                                       'cpu_time',
                                       'delayacct_blkio_time',
                                       'duration',
                                       'exitcode',
                                       'guest_time',
                                       'inblock',
                                       'invol_ctxsw',
                                       'majflt',
                                       'minflt',
                                       'num_procs',
                                       'num_threads',
                                       'outblock',
                                       'processor',
                                       'rchar',
                                       'rdtsc_duration',
                                       'read_bytes',
                                       'rssmax',
                                       'submit',
                                       'syscr',
                                       'syscw',
                                       'systemtime',
                                       'time_oncpu',
                                       'time_waiting',
                                       'timeslices',
                                       'updated_at',
                                       'usertime',
                                       'vol_ctxsw',
                                       'wchar',
                                       'write_bytes']))

    @db_session
    def test_job(self):
        j = Job['685000']
        self.assertEqual(j.jobid, '685000')
        jobs = eq.get_jobs(JOBS_LIST, fmt='terse')
        self.assertEqual(type(jobs), list, 'wrong jobs format with terse')
        self.assertEqual(len(jobs), 3, 'job count in db wrong')
        self.assertEqual(jobs, sorted(JOBS_LIST))
        df = eq.get_jobs(JOBS_LIST, fmt='pandas')
        # sqlalchemy has 4 fewer fields, which we eventually want to remove from
        # the job model
        self.assertIn(df.shape, ((3, 44), (3, 48)))
        # pony has some extra fields we don't care about and will probably remove:
        # 'account', 'jobscriptname', 'sessionid', 'queue'
        self.assertEqual(set(df.columns.values) - set(['account', 'jobscriptname', 'sessionid', 'queue']),
                         set(['PERF_COUNT_SW_CPU_CLOCK', 'all_proc_tags', 'analyses', 'annotations',
                              'cancelled_write_bytes', 'cpu_time', 'created_at', 'delayacct_blkio_time', 'duration',
                              'end', 'env_changes_dict', 'env_dict', 'exitcode', 'guest_time', 'inblock', 'info_dict',
                              'invol_ctxsw', 'jobid', 'jobname', 'majflt', 'minflt', 'num_procs', 'num_threads',
                              'outblock', 'processor', 'rchar', 'rdtsc_duration', 'read_bytes', 'rssmax', 'start',
                              'submit', 'syscr', 'syscw', 'systemtime', 'tags', 'time_oncpu', 'time_waiting',
                              'timeslices', 'updated_at', 'user', 'usertime', 'vol_ctxsw', 'wchar', 'write_bytes']))
        df = eq.get_jobs('685016', fmt='pandas')
        self.assertEqual(df['jobid'][0], '685016', "cannot specify job as a single job id string")
        self.assertEqual(df.shape[0], 1, "wrong selection of jobs when specified as a string")
        jobs = eq.get_jobs('685016, 685000', fmt='dict')
        self.assertEqual(len(jobs), 2, 'job count wrong when selected a comma-separated string')

    @db_session
    def test_job_advanced(self):
        jobs = eq.get_jobs(JOBS_LIST, fmt='terse', order=eq.desc(Job.start), limit=2, offset=1)
        self.assertEqual(jobs, ['685003', '685000'], 'job limit/offset not working')
        if settings.orm == 'sqlalchemy':
            jobs = eq.get_jobs(JOBS_LIST, fltr=(Job.jobid != '685000'), fmt='orm')
        else:
            jobs = eq.get_jobs(JOBS_LIST, fltr=lambda j: '685000' not in j.jobid, fmt='orm')
        self.assertEqual(jobs.count(), 2, 'jobs orm query with filter option')
        jobs = eq.get_jobs(JOBS_LIST, tags='exp_component:ocean_month_rho2_1x1deg', fmt='terse')
        self.assertEqual(len(jobs), 1)

        # empty tag check
        j = orm_get(Job, '685016')
        t = j.tags
        j.tags = {}
        orm_commit()
        jobs = eq.get_jobs(JOBS_LIST, tags='', fmt='terse')
        self.assertEqual(jobs, ['685016'], 'jobs query with empty tag option')
        jobs = eq.get_jobs(JOBS_LIST, tags={}, fmt='terse')
        self.assertEqual(jobs, ['685016'], 'jobs query with {} tag option')
        # restore tags
        j.tags = t
        orm_commit()

        jobs = eq.get_jobs(JOBS_LIST,
                           tags=['ocn_res:0.5l75;exp_component:ocean_cobalt_fdet_100',
                                 'ocn_res:0.5l75;exp_component:ocean_annual_rho2_1x1deg'],
                           fmt='terse')
        self.assertEqual(jobs, ['685000', '685003'])
        # df = eq.get_jobs(           order='eq.desc(j.duration)', limit=1, fmt='pandas')
        df = eq.get_jobs(JOBS_LIST, order=eq.desc(Job.duration), limit=1, fmt='pandas')
        self.assertEqual(df.shape[0], 1, 'job query with limit')
        self.assertEqual('685016', df.loc[0, 'jobid'], "jobs dataframe query with order")
        jobs = eq.get_jobs(JOBS_LIST, before=0, fmt='terse')
        self.assertEqual(jobs, sorted(JOBS_LIST))
        jobs = eq.get_jobs(JOBS_LIST, after=0, fmt='terse')
        self.assertEqual(jobs, [])
        jobs = eq.get_jobs(JOBS_LIST, before='06/15/2019 00:00', fmt='terse')
        self.assertEqual(jobs, [])
        jobs = eq.get_jobs(JOBS_LIST, after='06/15/2019 00:00', fmt='terse')
        self.assertEqual(jobs, sorted(JOBS_LIST))
        jobs = eq.get_jobs(JOBS_LIST, before=-30, fmt='terse')
        self.assertEqual(jobs, sorted(JOBS_LIST))
        jobs = eq.get_jobs(JOBS_LIST, after=-30, fmt='terse')
        self.assertEqual(jobs, [])
        # hosts
        jobs = eq.get_jobs(JOBS_LIST, hosts=[], fmt='terse')
        self.assertEqual(set(jobs), set(JOBS_LIST))
        jobs = eq.get_jobs(JOBS_LIST, hosts=['pp208', 'pp212'], fmt='terse')
        self.assertEqual(jobs, ['685000', '685003'])
        jobs = eq.get_jobs(set(JOBS_LIST), hosts=['pp208', 'pp209', 'pp212'], fmt='terse')
        self.assertEqual(jobs, sorted(['685003', '685000']))
        jobs = eq.get_jobs(JOBS_LIST, hosts=['pp208', 'pp313', 'pp212'], fmt='terse')
        self.assertEqual(jobs, sorted(JOBS_LIST))
        # when
        jobs = eq.get_jobs(JOBS_LIST, when='06/15/2019 08:00', fmt='terse')
        self.assertEqual(jobs, sorted(JOBS_LIST))
        jobs = eq.get_jobs(JOBS_LIST, when='06/15/2019 07:00', fmt='terse')
        self.assertEqual(jobs, [])
        jobs = eq.get_jobs(JOBS_LIST, when='06/15/2019 09:00', fmt='terse')
        self.assertEqual(jobs, sorted(JOBS_LIST))
        jobs = eq.get_jobs(JOBS_LIST, when='06/15/2019 10:00', fmt='terse')
        self.assertEqual(jobs, [])
        jobs = eq.get_jobs(JOBS_LIST, when=orm_get(Job, '685003'), fmt='terse')
        self.assertEqual(jobs, sorted(JOBS_LIST))
        # hosts + when
        jobs = eq.get_jobs(JOBS_LIST, hosts='pp208', when='06/15/2019 08:00', fmt='terse')
        self.assertEqual(jobs, ['685000'])
        jobs = eq.get_jobs(JOBS_LIST, hosts='pp208', when='06/15/2019 11:00', fmt='terse')
        self.assertEqual(jobs, [])
        jobs = eq.get_jobs(JOBS_LIST, when='06/15/2019 08:00', hosts=['pp208', 'pp212'], fmt='terse')
        self.assertEqual(jobs, sorted(['685003', '685000']))
        jobs = eq.get_jobs(JOBS_LIST, when='06/16/2019 08:00', hosts=['pp208', 'pp212'], fmt='terse')
        self.assertEqual(jobs, [])

    @db_session
    def test_procs(self):
        procs = eq.get_procs(['685016'], fmt='terse')
        self.assertEqual(type(procs), list, 'wrong procs format with terse')
        self.assertEqual(len(procs), 3412, 'wrong count of processes in terse')
        procs = eq.get_procs(['685016', '685000'], fmt='orm')
        self.assertEqual(procs.count(), 6892, 'wrong count of processes in ORM format')
        df = eq.get_procs(JOBS_LIST, fmt='pandas', limit=10)
        self.assertIn(df.shape, ((10, 50), (10, 49)))
        procs_limit = eq.get_procs(fmt='terse')
        self.assertNotEqual(len(procs_limit), 10000)
        procs_unlimited = eq.get_procs(fmt='orm')
        self.assertNotEqual(procs_unlimited.count(), 10000)

    @db_session
    def test_procs_convert(self):
        # check and ensure that we cannot run a conversion on the full db!
        with self.assertRaises(ValueError):
            eq.conv_procs([])
        with self.assertRaises(ValueError):
            eq.conv_procs(None)

        for inform in ['terse', 'dict', 'pandas', 'orm']:
            procs = eq.get_procs('685000', order=Process.start, fmt=inform)
            self.assertEqual(procs.count() if inform == 'orm' else len(procs), 3480)
            for outform in ['terse', 'dict', 'pandas', 'orm']:
                procs2 = eq.conv_procs(procs, fmt=outform)
                if isinstance(procs, pd.DataFrame):
                    self.assertTrue(eq.conv_procs(procs2, fmt=inform, order=Process.start).equals(procs))
                else:
                    if inform != 'orm':
                        self.assertEqual(eq.conv_procs(procs2, fmt=inform, order=Process.start), procs)

    @db_session
    def test_procs_advanced(self):
        if settings.orm == 'sqlalchemy':
            procs = eq.get_procs(
                JOBS_LIST, fltr=(
                    Process.duration > 1000000), order=eq.desc(
                    Process.duration), fmt='orm')
        else:
            procs = eq.get_procs(JOBS_LIST, fltr=lambda p: p.duration > 1000000, order='desc(p.duration)', fmt='orm')
        self.assertEqual(procs.count(), 630, 'wrong count of processes in ORM format using filter')
        self.assertEqual(int(procs.first().duration), 7005558348, 'wrong order when using orm with filter and order')

        df = eq.get_procs(JOBS_LIST, limit=5, order=eq.desc(Process.cpu_time), fmt='pandas')
        self.assertIn(df.shape, ((5, 50), (5, 49)))
        self.assertEqual('685016', df.loc[0, 'job'], "ordering of processes wrong in dataframe")

        # Tags
        # empty tag query
        procs1 = eq.get_procs(tags='', fmt='terse')
        procs2 = eq.get_procs(tags={}, fmt='terse')
        self.assertEqual(len(procs2), len(procs1))
        p = eq.get_procs(tags='op_sequence:1', limit=1, fmt='orm')[0]
        p.tags = {}
        orm_commit()
        procs = eq.get_procs(tags={}, fmt='terse')
        self.assertEqual(len(procs), len(procs1) + 1)

        if settings.orm == 'sqlalchemy':
            procs_with_tag = eq.get_procs(
                JOBS_LIST, tags='op_sequence:4', fltr=(
                    Process.duration > 10000000), order=eq.desc(
                    Process.duration), fmt='orm')
        else:
            procs_with_tag = eq.get_procs(
                JOBS_LIST,
                tags='op_sequence:4',
                fltr='p.duration > 10000000',
                order='desc(p.duration)',
                fmt='orm')
        self.assertEqual(procs_with_tag.count(), 2, 'incorrect process count when using tag and filter')
        if settings.orm == 'sqlalchemy':
            procs_with_tag = eq.get_procs(
                JOBS_LIST, tags={
                    'op_sequence': 4}, fltr=(
                    Process.duration > 10000000), order=eq.desc(
                    Process.duration), fmt='orm')
        else:
            procs_with_tag = eq.get_procs(
                JOBS_LIST,
                tags={
                    'op_sequence': 4},
                fltr='p.duration > 10000000',
                order='desc(p.duration)',
                fmt='orm')
        self.assertEqual(procs_with_tag.count(), 2)
        p = procs_with_tag.first()
        self.assertEqual(int(p.duration), 207384313)
        if settings.orm == 'sqlalchemy':
            self.assertEqual(len(p.descendants[:]), 85)
        else:
            self.assertEqual(p.descendants.count(), 85)

        self.assertEqual(eq.get_procs(JOBS_LIST, tags='op_sequence:4', fmt='orm').count(), 270)
        self.assertEqual(eq.get_procs(JOBS_LIST, tags='op_sequence:5', fmt='orm').count(), 285)
        self.assertEqual(eq.get_procs(JOBS_LIST, tags=['op_sequence:4', 'op_sequence:5'], fmt='orm').count(), 555)
        s1 = set(eq.get_procs(JOBS_LIST, tags='op_sequence:5', fmt='terse'))
        s2 = set(eq.get_procs(JOBS_LIST, tags='op_sequence:4', fmt='terse'))
        s = set(eq.get_procs(JOBS_LIST, tags=['op_sequence:4', 'op_sequence:5'], fmt='terse'))
        self.assertEqual(s, s1 | s2)

        # hosts, when
        procs = eq.get_procs('685000', when=datetime(2019, 6, 15, 7, 53), fmt='orm')
        pids = [p.pid for p in procs]
        self.assertEqual(set(pids), set([6098, 6226]))
        procs = eq.get_procs('685000', when='06/15/2019 07:53', fmt='orm')
        pids = [p.pid for p in procs]
        self.assertEqual(set(pids), set([6098, 6226]))
        self.assertEqual(eq.get_procs('685000', hosts=['pp208'], fmt='orm').count(), 3480)
        self.assertEqual(eq.get_procs('685000', hosts=['pp208', 'pp209'], fmt='orm').count(), 3480)
        self.assertEqual(eq.get_procs('685000', hosts=['pp209'], fmt='orm').count(), 0)
        self.assertEqual(eq.get_procs(['685000', '685003'], hosts=['pp208', 'pp212'], fmt='orm').count(),
                         7265)
        self.assertEqual(eq.get_procs(['685000', '685003'], hosts=['pp212'], fmt='orm').count(), 3785)

    @db_session
    def test_process_tree(self):
        from epmt.epmt_job import mk_process_tree
        mk_process_tree('685000')
        p = eq.get_procs('685000', fmt='orm', order=eq.desc(Process.start), limit=1)[0]
        self.assertEqual(p.depth, 3)
        root = eq.root('685000', fmt='orm')
        self.assertEqual(root.depth, 0)

        # now let's check the children/descendant counts
        p = eq.get_procs(
            fltr=(
                Process.pid == 6098) if settings.orm == 'sqlalchemy' else (
                lambda p: p.pid == 6098),
            fmt='orm').first()
        self.assertEqual(len(p.children), 735)
        self.assertEqual(len(p.descendants), 3448)
        from hashlib import md5
        self.assertEqual(md5(", ".join(sorted([str(proc.pid) for proc in p.children])).encode(
            'utf-8')).hexdigest(), '32c538b6313427ebd7a634ca1ea36de0')
        self.assertEqual(md5(", ".join(sorted([str(proc.pid) for proc in p.descendants])).encode(
            'utf-8')).hexdigest(), 'f0dfe011c0df53e3329324a2ca8f9b3e')
        p = eq.get_procs(
            fltr=(
                Process.pid == 26860) if settings.orm == 'sqlalchemy' else (
                lambda p: p.pid == 26860),
            fmt='orm').first()
        self.assertEqual(p.parent.pid, 26859)
        self.assertEqual(set([proc.pid for proc in p.ancestors]), set([6098, 26859]))

    @db_session
    def test_job_convert(self):
        # check and ensure that we cannot run a conversion on the full db!
        with self.assertRaises(ValueError):
            eq.conv_jobs([])
        with self.assertRaises(ValueError):
            eq.conv_jobs(None)

        for fmt in ['dict', 'terse', 'pandas', 'orm']:
            jobs = eq.get_jobs(['685000', '685003'], fmt=fmt)
            self.assertEqual(set(eq.conv_jobs(jobs, fmt='terse')), set(['685000', '685003']))
            j1 = orm_get(Job, '685000')
            j2 = orm_get(Job, '685003')
            self.assertEqual(set(eq.conv_jobs(jobs, fmt='orm')[:]), set([j1, j2]))
            self.assertEqual(set(eq.conv_jobs(jobs, fmt='pandas')['jobid'].values), set(['685000', '685003']))
            self.assertEqual(set([j['jobid'] for j in eq.conv_jobs(jobs, fmt='dict')]), set(['685000', '685003']))

        ref = eq.get_jobs(JOBS_LIST, fmt='terse')
        for inp_fmt in ['terse', 'orm', 'pandas', 'dict']:
            jobs = eq.get_jobs(JOBS_LIST, fmt=inp_fmt)
            for out_fmt in ['pandas', 'terse', 'orm', 'dict']:
                out = eq.conv_jobs(jobs, fmt=out_fmt)
                if out_fmt == 'terse':
                    self.assertEqual(type(out), list, 'output format not terse when input fmt: {0}'.format(inp_fmt))
                    self.assertEqual(sorted(out), sorted(ref), 'error in {0} -> {1}'.format(inp_fmt, out_fmt))
                elif out_fmt == 'orm':
                    self.assertTrue(orm_is_query(out), 'output format not ORM when input fmt: {0}'.format(inp_fmt))
                    self.assertEqual(sorted([j.jobid for j in out]), sorted(
                        ref), 'error in {0} -> {1}'.format(inp_fmt, out_fmt))
                elif out_fmt == 'dict':
                    self.assertTrue(
                        isinstance(out, list) and len(out) > 0 and isinstance(out[0], dict),
                        'output format not dictlist when input fmt: {0}'.format(inp_fmt))
                    self.assertEqual(sorted([j['jobid'] for j in out]), sorted(ref),
                                     'error in {0} -> {1}'.format(inp_fmt, out_fmt))
                elif out_fmt == 'pandas':
                    self.assertEqual(
                        type(out),
                        pd.DataFrame,
                        'output format not dataframe when input fmt: {0}'.format(inp_fmt))
                    self.assertEqual(sorted(list(out['jobid'].values)), sorted(ref),
                                     'error in {0} -> {1}'.format(inp_fmt, out_fmt))

    @db_session
    def test_job_proc_tags(self):
        with self.assertRaises(ValueError):
            eq.job_proc_tags([], fold=False)
        tags = eq.job_proc_tags(['685000', '685016'], fold=False)
        self.assertEqual(len(tags), 89, "wrong unique process tags count")
        tags = [str_dict(d) for d in tags]
        from hashlib import md5
        self.assertEqual(md5(str(tags).encode('utf-8')).hexdigest(),
                         'bd7eabf266aa5b179bbe4d65b35bd47f', 'wrong hash for job_proc_tags')
        sk = eq.rank_proc_tags_keys(['685000'])
        self.assertEqual(sk[0], ('op', {'ncatted', 'ncrcat', 'dmput', 'fregrid',
                         'rm', 'timavg', 'hsmget', 'mv', 'cp', 'splitvars', 'untar'}))

    @db_session
    def test_op(self):
        op = Operation(['685000'], {'op': 'timavg'})
        self.assertEqual((op.tags, op.duration), ({'op': 'timavg'}, 41388496.0))
        self.assertEqual(op.proc_sums,
                         {'syscr': 127808, 'guest_time': 0, 'inblock': 0, 'processor': 0, 'rchar': 5356358342,
                          'cancelled_write_bytes': 45056, 'outblock': 5139208, 'timeslices': 2661,
                          'PERF_COUNT_SW_CPU_CLOCK': 17547070414, 'wchar': 5262916589, 'rssmax': 7854752, 'numtids': 62,
                          'duration': 41388496.0, 'read_bytes': 0, 'time_waiting': 35814116, 'delayacct_blkio_time': 0,
                          'invol_ctxsw': 1884, 'majflt': 0, 'syscw': 80433, 'minflt': 92584, 'cpu_time': 17951212.0,
                          'vol_ctxsw': 714, 'time_oncpu': 17984466575, 'rdtsc_duration': 153196621348,
                          'systemtime': 4074354, 'num_procs': 57, 'write_bytes': 2631274496, 'usertime': 13876858})
        op = Operation(['685000'], {'op': 'timavg'}, op_duration_method="sum-minus-overlap")
        self.assertEqual((op.tags, op.duration, op.num_runs()), ({'op': 'timavg'}, 21033390.0, 11))
        self.assertEqual(op.proc_sums,
                         {'syscr': 127808, 'guest_time': 0, 'inblock': 0, 'processor': 0, 'rchar': 5356358342,
                          'cancelled_write_bytes': 45056, 'outblock': 5139208, 'timeslices': 2661,
                          'PERF_COUNT_SW_CPU_CLOCK': 17547070414, 'wchar': 5262916589, 'rssmax': 7854752, 'numtids': 62,
                          'duration': 21033390.0, 'read_bytes': 0, 'time_waiting': 35814116, 'delayacct_blkio_time': 0,
                          'invol_ctxsw': 1884, 'majflt': 0, 'syscw': 80433, 'minflt': 92584, 'cpu_time': 17951212.0,
                          'vol_ctxsw': 714, 'time_oncpu': 17984466575, 'rdtsc_duration': 153196621348,
                          'systemtime': 4074354, 'num_procs': 57, 'write_bytes': 2631274496, 'usertime': 13876858})
        op = Operation(['685000'], {'op': 'timavg'}, op_duration_method="finish-minus-start")
        self.assertEqual((op.tags, op.duration), ({'op': 'timavg'}, 51278054.0))
        self.assertEqual(op.proc_sums,
                         {'syscr': 127808, 'guest_time': 0, 'inblock': 0, 'processor': 0, 'rchar': 5356358342,
                          'cancelled_write_bytes': 45056, 'outblock': 5139208, 'timeslices': 2661,
                          'PERF_COUNT_SW_CPU_CLOCK': 17547070414, 'wchar': 5262916589, 'rssmax': 7854752, 'numtids': 62,
                          'duration': 51278054.0, 'read_bytes': 0, 'time_waiting': 35814116, 'delayacct_blkio_time': 0,
                          'invol_ctxsw': 1884, 'majflt': 0, 'syscw': 80433, 'minflt': 92584, 'cpu_time': 17951212.0,
                          'vol_ctxsw': 714, 'time_oncpu': 17984466575, 'rdtsc_duration': 153196621348,
                          'systemtime': 4074354, 'num_procs': 57, 'write_bytes': 2631274496, 'usertime': 13876858})
        self.assertEqual(set(op.to_dict().keys()),
                         {'jobs',
                          'proc_sums',
                          'duration',
                          'tags',
                          'exact_tag_only',
                          'start',
                          'finish',
                          'op_duration_method'})
        self.assertEqual(set(op.to_dict(full=True).keys()),
                         {'jobs',
                          'proc_sums',
                          'duration',
                          'tags',
                          'processes',
                          'exact_tag_only',
                          'start',
                          'finish',
                          'intervals',
                          'num_runs',
                          'contiguous',
                          'op_duration_method'})
        op = Operation(['685000', '685003'], {'op': 'timavg'})
        self.assertEqual(op.proc_sums,
                         {'syscw': 89297, 'PERF_COUNT_SW_CPU_CLOCK': 29297709455, 'time_oncpu': 32531383700,
                          'usertime': 25906808, 'time_waiting': 81086345, 'timeslices': 8001,
                          'cancelled_write_bytes': 262144, 'outblock': 5665088, 'guest_time': 0, 'minflt': 647328,
                          'invol_ctxsw': 3996, 'processor': 0, 'rssmax': 10901764, 'read_bytes': 7303168,
                          'rdtsc_duration': 244679507379, 'inblock': 14264, 'majflt': 18, 'num_procs': 428,
                          'write_bytes': 2900525056, 'delayacct_blkio_time': 0, 'duration': 67847274.0, 'syscr': 206204,
                          'rchar': 8118076508, 'cpu_time': 32325636.0, 'systemtime': 6418828, 'wchar': 5805294586,
                          'vol_ctxsw': 3571, 'numtids': 433})

    @db_session
    def test_op_metrics(self):
        with self.assertRaises(ValueError):
            eq.get_op_metrics([])
        df = eq.get_op_metrics(['685000', '685016'])
        self.assertEqual(df.shape, (178, 31), "wrong dataframe shape for get_op_metrics")
        top = df[['job', 'tags', 'duration']].sort_values('duration', axis=0, ascending=False)[:1]
        self.assertEqual(top.tags.values[0], {'op_instance': '2', 'op_sequence': '89', 'op': 'dmput'})
        self.assertEqual(int(top.duration.values[0]), 7008334182)

        df = eq.get_op_metrics(['685000', '685016'], op_duration_method="sum-minus-overlap")
        top = df[['job', 'tags', 'duration']].sort_values('duration', axis=0, ascending=False)[:1]
        self.assertEqual(int(top.duration.values[0]), 7005558348)

        df = eq.get_op_metrics(['685000', '685016'], tags='op_sequence:89')
        # pylint: disable=no-member
        self.assertEqual([int(f) for f in list(df.duration.values)], [6463542235, 7008334182])
        df = eq.get_op_metrics(['685000', '685016'], tags='op_sequence:89', op_duration_method="sum-minus-overlap")
        # pylint: disable=no-member
        self.assertEqual([int(f) for f in list(df.duration.values)], [6460188134, 7005558348])
        df = eq.get_op_metrics(['685000', '685016'], tags='op_sequence:89', op_duration_method="finish-minus-start")
        # pylint: disable=no-member
        self.assertEqual([int(f) for f in list(df.duration.values)], [6460188134, 7005558348])

        df = eq.get_op_metrics(['685000', '685003', '685016'])
        self.assertEqual(df.shape, (573, 31), 'wrong get_op_metrics shape when no tag specified')
        # pylint: disable=no-member
        self.assertEqual([int(x) for x in df.cpu_time.values][:10], [1207637., 1268652., 1225636.,
                         1263656., 1315618., 1261654., 1209636., 1246659., 1205634., 1265656.])

        df = eq.get_op_metrics(['685000', '685003', '685016'], tags=['op:hsmget', 'op:mv'])
        self.assertEqual(df.shape, (6, 31), 'wrong get_op_metrics shape with tags specified')
        # pylint: disable=no-member
        self.assertEqual([int(x) for x in df.cpu_time.values], [
                         53934101, 31337553, 123305670, 2799492, 20996147, 6496944])
        # self.assertEqual([int(x) for x in df.duration.values], [6375786656, 6471901800, 6672575160, 8551396, 69194108, 17359881])
        # self.assertEqual([int(x) for x in df.duration.values], [6378342472, 6474000335, 6674198021, 67199129, 133578518, 287555579])
        # pylint: disable=no-member
        self.assertEqual(
            list(
                df.tags.values), [
                {
                    'op': 'hsmget'}, {
                    'op': 'hsmget'}, {
                        'op': 'hsmget'}, {
                            'op': 'mv'}, {
                                'op': 'mv'}, {
                                    'op': 'mv'}])

    @db_session
    def test_op_metrics_grouped(self):
        df = eq.get_op_metrics(['685000', '685003', '685016'], group_by_tag=True)
        self.assertEqual(df.shape, (459, 29), 'wrong get_op_metrics grouped shape when no tag specified')
        self.assertEqual(list(df['tags'].values[:10]),
                         [{'op_instance': '11', 'op_sequence': '66', 'op': 'cp'},
                          {'op_instance': '15', 'op_sequence': '79', 'op': 'cp'},
                          {'op_instance': '3', 'op_sequence': '247', 'op': 'cp'},
                          {'op_instance': '3', 'op_sequence': '251', 'op': 'cp'},
                          {'op_instance': '3', 'op_sequence': '255', 'op': 'cp'},
                          {'op_instance': '3', 'op_sequence': '259', 'op': 'cp'},
                          {'op_instance': '3', 'op_sequence': '263', 'op': 'cp'},
                          {'op_instance': '3', 'op_sequence': '267', 'op': 'cp'},
                          {'op_instance': '3', 'op_sequence': '271', 'op': 'cp'},
                          {'op_instance': '3', 'op_sequence': '30', 'op': 'cp'}],
                         'wrong tags ordering in grouped get_op_metrics')
        # pylint: disable=no-member
        self.assertEqual(
            list(
                df.cpu_time.values)[
                :10], [
                2476289.0, 2489292.0, 472905.0, 462906.0, 461906.0, 465903.0, 471904.0, 485902.0, 472905.0, 2577272.0])

        df = eq.get_op_metrics(['685000', '685003', '685016'], tags=['op:hsmget', 'op:mv'], group_by_tag=True)
        self.assertEqual(df.shape, (2, 29), 'wrong get_op_metrics shape with tags specified')
        # pylint: disable=no-member
        self.assertEqual(list(df.tags.values), [{'op': 'hsmget'}, {'op': 'mv'}])
        self.assertEqual(list(df['cpu_time'].values), [208577324.0, 30292583.0])

    @db_session
    def test_ops(self):
        ops = eq.get_ops(['685000', '685003'], tags=['op:timavg', 'op:ncks'])
        self.assertEqual([type(op) for op in ops], [dict, dict])
        self.assertEqual((ops[0]['proc_sums']['num_procs'], ops[1]['proc_sums']['num_procs']), (428, 190))
        self.assertEqual((ops[0]['proc_sums']['cpu_time'], ops[1]['proc_sums']['cpu_time']), (32325636.0, 6484854.0))
        self.assertEqual((ops[0]['duration'], ops[1]['duration']), (67847274.0, 4787122.0))
        ops = eq.get_ops(['685000', '685003'], tags=['op:timavg', 'op:ncks'], fmt='pandas')
        self.assertEqual(ops.shape, (2, 8))

        ops = eq.get_ops(['685000', '685003'], tags=['op:timavg', 'op:ncks'], op_duration_method="sum-minus-overlap")
        self.assertEqual((ops[0]['duration'], ops[1]['duration']), (36053215.0, 4773815.0))
        ops = eq.get_ops(['685000', '685003'], tags=['op:timavg', 'op:ncks'], op_duration_method="finish-minus-start")
        self.assertEqual((ops[0]['duration'], ops[1]['duration']), (232727177.0, 131928185.0))

        ops = eq.get_ops(['685000', '685003'], tags=['op:timavg', 'op:ncks'], combine=True, fmt='orm')
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0].proc_sums['num_procs'], 618)

        ops = eq.get_ops(['685000', '685003'], tags='op', combine=True)
        self.assertEqual(len(ops), 1)
        op = ops[0]
        self.assertEqual((op['proc_sums']['num_procs'], op['proc_sums']['numtids']), (7111, 7544))
        ops2 = eq.get_ops(['685000', '685003'], tags='', combine=True)
        self.assertEqual(ops2, ops)

    @db_session
    def test_root(self):
        p = eq.root('685016')
        self.assertEqual((p['pid'], p['exename']), (122181, 'tcsh'))
        p = eq.root('685016', fmt='orm')
        self.assertEqual(p.pid, 122181)
        df = eq.root('685016', fmt='pandas')
        self.assertIn(df.shape, ((1, 50), (1, 49)))
        self.assertEqual(df.loc[0, 'pid'], 122181)

    def test_job_tags(self):
        d = eq.get_job_tags(['685016', '685003', '685000'],
                            tag_filter='exp_name:ESM4_historical_D151;exp_time:18840101')
        self.assertEqual(set(d.keys()), {'atm_res', 'exp_component', 'exp_name', 'exp_time', 'ocn_res', 'script_name'})
        self.assertEqual(d,
                         {'atm_res': 'c96l49',
                          'ocn_res': '0.5l75',
                          'exp_name': 'ESM4_historical_D151',
                          'exp_time': '18840101',
                          'script_name': {'ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101',
                                          'ESM4_historical_D151_ocean_month_rho2_1x1deg_18840101',
                                          'ESM4_historical_D151_ocean_cobalt_fdet_100_18840101'},
                             'exp_component': {'ocean_month_rho2_1x1deg',
                                               'ocean_annual_rho2_1x1deg',
                                               'ocean_cobalt_fdet_100'}})

    @db_session
    def test_job_roots(self):
        pids = [p.pid for p in eq.get_roots(['685000', '685003'], fmt='orm')]
        self.assertEqual(pids,
                         [6098, 29001, 31171, 31291, 10015, 10168, 32139, 11002, 32315, 11172, 1311, 1490, 12990, 13118,
                          13220, 1652, 1941, 13597, 14403, 14547, 2321, 2655, 26466, 26469, 26500, 26726, 26729, 26760,
                          26986, 26989, 27020, 27246, 27249, 27280, 27506, 27509, 27540, 27775, 27833, 27836, 27867,
                          28093, 28129, 8082, 8179, 8231, 8283, 8335, 8387, 8439, 8491, 8543, 8603, 8655, 8707, 8863,
                          8997, 9044, 9090, 9126, 9162, 9198, 9237, 9881, 9930, 9979, 10028, 10077, 10126, 10175])

    @db_session
    def test_jobs_annotations(self):
        r = eq.annotate_job('685000', {'abc': 100}, replace=True)
        self.assertEqual(r, {'abc': 100})
        self.assertEqual(eq.get_job_annotations('685000'), {'abc': 100})
        r = eq.annotate_job('685000', {'def': 'hello'})
        self.assertEqual(r, {'abc': 100, 'def': 'hello'})
        self.assertEqual(eq.get_job_annotations('685000'), {'abc': 100, 'def': 'hello'})
        self.assertEqual(eq.get_jobs(annotations={'abc': 100}, fmt='terse'), ['685000'])
        r = eq.annotate_job('685000', {'def': 'hello'}, True)
        self.assertEqual(r, {'def': 'hello'})
        self.assertEqual(eq.get_job_annotations('685000'), {'def': 'hello'})
        r = eq.remove_job_annotations('685000')
        self.assertEqual(r, {})
        self.assertEqual(eq.get_job_annotations('685000'), {})
        r = eq.annotate_job('685016', 'abc:200;def:bye')
        self.assertEqual(
            r,
            {
                'abc': '200',
                'def': 'bye',
                'EPMT_JOB_TAGS': 'atm_res:c96l49;exp_component:ocean_month_rho2_1x1deg;exp_name:ESM4_historical_D151;exp_time:18840101;ocn_res:0.5l75;script_name:ESM4_historical_D151_ocean_month_rho2_1x1deg_18840101'})
        self.assertEqual(
            eq.get_job_annotations('685016'),
            {
                'abc': '200',
                'def': 'bye',
                'EPMT_JOB_TAGS': 'atm_res:c96l49;exp_component:ocean_month_rho2_1x1deg;exp_name:ESM4_historical_D151;exp_time:18840101;ocn_res:0.5l75;script_name:ESM4_historical_D151_ocean_month_rho2_1x1deg_18840101'})
        self.assertEqual(eq.get_jobs(annotations={'abc': '200'}, fmt='terse'), ['685016'])

    @db_session
    def test_jobs_comparable(self):
        self.assertEqual(sorted(eq.comparable_job_partitions(['685000', '685003', '685016']), key=lambda v: v[1][0]),
                         [(('ESM4_historical_D151', 'ocean_annual_rho2_1x1deg'), ['685000']),
                          (('ESM4_historical_D151', 'ocean_cobalt_fdet_100'), ['685003']),
                          (('ESM4_historical_D151', 'ocean_month_rho2_1x1deg'), ['685016'])])
        self.assertFalse(eq.are_jobs_comparable(['685000', '685003', '685016']))

    @db_session
    def test_unanalyzed_jobs(self):
        uj = eq.get_unanalyzed_jobs(['685000', '685003', '685016'])
        self.assertEqual(set(uj), set(['685000', '685003', '685016']))
        self.assertEqual(eq.get_job_analyses('685000'), {})
        r = eq.set_job_analyses('685000', {'outlier_detection': 1})
        self.assertEqual(r, {'outlier_detection': 1})
        self.assertEqual(eq.get_job_analyses('685000'), {'outlier_detection': 1})
        uj = eq.get_unanalyzed_jobs(['685000', '685003', '685016'])
        self.assertEqual(set(uj), set(['685003', '685016']))
        r = eq.set_job_analyses('685000', {'rca': 1})
        self.assertEqual(r, {'outlier_detection': 1, 'rca': 1})
        self.assertEqual(eq.get_job_analyses('685000'), {'outlier_detection': 1, 'rca': 1})
        self.assertEqual(eq.get_jobs(analyses={'rca': 1}, fmt='terse'), ['685000'])
        r = eq.set_job_analyses('685000', {'rca': 1}, True)
        self.assertEqual(r, {'rca': 1})
        self.assertEqual(eq.get_job_analyses('685000'), {'rca': 1})
        # get back to pristine state
        r = eq.remove_job_analyses('685000')
        self.assertEqual(r, {})
        self.assertEqual(eq.get_job_analyses('685000'), {})
        uj = eq.get_unanalyzed_jobs(['685000', '685003', '685016'])
        self.assertEqual(set(uj), set(['685000', '685003', '685016']))
        eq.analyze_jobs(['685000', '685003', '685016'])
        uj = eq.get_unanalyzed_jobs(['685000', '685003', '685016'])
        self.assertEqual(set(uj), set([]))

    @db_session
    def test_op_roots(self):
        with self.assertRaises(ValueError):
            eq.op_roots([], 'op_sequence:4', fmt='orm')
        op_root_procs = eq.op_roots(['685000', '685003'], 'op_sequence:4', fmt='orm')
        self.assertEqual(set([p.pid for p in op_root_procs]), set([11023, 11185, 11187, 32160, 32328, 32330]))
        # op_root_procs = eq.op_roots(['685000', '685003', '685016'], 'op_sequence:1', fmt='orm')
        # l = eq.select((p.job.jobid, p.pid) for p in op_root_procs)[:]
        # self.assertEqual(l,
        #                 [ ('685000', 6226), ('685000', 10042), ('685000', 10046), ('685000', 10058), ('685000', 10065),
        #                   ('685000', 10066), ('685003', 29079), ('685003', 31184), ('685003', 31185), ('685003', 31191),
        #                   ('685003', 31198), ('685003', 31199), ('685016', 122259), ('685016', 128848), ('685016', 128849),
        #                   ('685016', 128855), ('685016', 128862), ('685016', 128863)])
        df = eq.op_roots(['685000', '685003', '685016'], 'op_sequence:1', fmt='pandas')
        self.assertIn(df.shape, ((18, 50), (18, 49)))
        self.assertEqual(set(df['pid'].values),
                         set([6226, 10042, 10046, 10058, 10065, 10066, 29079,
                              31184, 31185, 31191, 31198, 31199,
                              122259, 128848, 128849, 128855, 128862, 128863]))

    @db_session
    def test_timeline(self):
        jobs = eq.get_jobs(JOBS_LIST, fmt='orm')
        procs = eq.timeline(jobs, fmt='orm')
        # p1 = procs.first()
        # self.assertEqual(p1.start, min(min(j.processes.start) for j in jobs))
        self.assertEqual([p.start for p in procs[:3]],
                         [datetime(2019, 6, 15, 7, 52, 4, 126892),
                          datetime(2019, 6, 15, 7, 52, 4, 133795),
                          datetime(2019, 6, 15, 7, 52, 4, 142141)])
        procs = eq.timeline('685016', fmt='orm', limit=5)
        pids = [p.pid for p in procs]
        self.assertEqual(pids, [122181, 122182, 122183, 122184, 122185])

    @db_session
    def test_refmodel_crud(self):
        jobs = eq.get_jobs(JOBS_LIST, fmt='terse')
        self.assertEqual(len(jobs), 3)
        # jobs = eq.get_jobs(JOBS_LIST, fmt='orm')
        # self.assertEqual(jobs.count(), 3)
        model_name = 'test_model'
        with capture() as (out, err):
            r = eq.create_refmodel(jobs, tag='model_name:' + model_name)
        self.assertIn('WARNING: The jobs do not share identical tag values', err.getvalue())
        self.assertEqual(r['tags'], {'model_name': model_name})
        self.assertTrue(eq.get_refmodels())
        rq = eq.get_refmodels(tag='model_name:' + model_name, fmt='orm')
        self.assertEqual(rq.count(), 1)
        r1 = rq.first()
        self.assertEqual(r1.id, r['id'])
        self.assertEqual(r1.tags, {'model_name': model_name})
        self.assertFalse(r1.op_tags)
        self.assertEqual(set([j.jobid for j in r1.jobs]), set(jobs))

        # model metrics: get/set
        all_metrics = eq.refmodel_get_metrics(r1.id, False)
        self.assertEqual(set(all_metrics), {'duration', 'num_procs', 'cpu_time'})
        active_metrics = eq.refmodel_get_metrics(r1.id, True)
        self.assertEqual(set(active_metrics), {'duration', 'num_procs', 'cpu_time'})
        eq.refmodel_set_active_metrics(r1.id, ['duration', 'cpu_time'])
        # all metrics will be the same as before, but active metrics will change
        all_metrics = eq.refmodel_get_metrics(r1.id, False)
        self.assertEqual(set(all_metrics), {'duration', 'num_procs', 'cpu_time'})
        active_metrics = eq.refmodel_get_metrics(r1.id, True)
        self.assertEqual(set(active_metrics), {'duration', 'cpu_time'})
        # restore the metrics for model
        eq.refmodel_set_active_metrics(r1.id, ['duration', 'cpu_time', 'num_procs'])
        active_metrics = eq.refmodel_get_metrics(r1.id, True)
        self.assertEqual(set(active_metrics), {'duration', 'num_procs', 'cpu_time'})

        # check enabled
        self.assertTrue(eq.refmodel_is_enabled(r1.id))
        eq.refmodel_set_enabled(r1.id, enabled=False)
        self.assertFalse(eq.refmodel_is_enabled(r1.id))
        # delete model
        n = eq.delete_refmodels(r['id'])
        self.assertEqual(n, 1, 'wrong ref_model delete count')
        # wildcard features
        with capture() as (out, err):
            r = eq.create_refmodel(jobs, tag='model_name:' + model_name, features='*')
        all_features = {
            'duration',
            'syscr',
            'systemtime',
            'PERF_COUNT_SW_CPU_CLOCK',
            'cpu_time',
            'delayacct_blkio_time',
            'time_waiting',
            'write_bytes',
            'inblock',
            'minflt',
            'invol_ctxsw',
            'syscw',
            'wchar',
            'num_threads',
            'processor',
            'cancelled_write_bytes',
            'rssmax',
            'rchar',
            'outblock',
            'num_procs',
            'time_oncpu',
            'rdtsc_duration',
            'usertime',
            'timeslices',
            'guest_time',
            'vol_ctxsw',
            'majflt',
            'read_bytes',
            'exitcode'}
        self.assertEqual(eq.refmodel_get_metrics(r['id'], False), all_features)  # all metrics
        self.assertEqual(eq.refmodel_get_metrics(r['id'], True), all_features)  # active metrics
        eq.delete_refmodels(r['id'])

        # named reference models
        with capture() as (out, err):
            r1 = eq.create_refmodel(jobs, name='test_model')
            r2 = eq.create_refmodel(jobs)
        self.assertEqual(r1['name'], 'test_model')
        self.assertEqual([r1['id']], eq.get_refmodels(name='test_model', fmt='terse'))
        self.assertFalse(eq.get_refmodels(name='no_such_model'))
        eq.delete_refmodels(r1['id'], r2['id'])

    # @db_session
    # def test_ops_dm_calc(self):
    #     jobs = eq.get_jobs(['685000', '685003', '685016'], fmt='orm')
    #     self.assertEqual(jobs.count(), 3)
    #     (perc, df, j_cpu) = eq.dm_calc(jobs)
    #     self.assertEqual(perc, 43.16)
    #     self.assertEqual(df.shape, (6, 29))
    #     self.assertEqual(df['cpu_time'].sum(), 273510353.0)
    #     self.assertEqual(j_cpu, 633756327.0)

    @db_session
    def test_ops_costs(self):
        jobs = eq.get_jobs(['685000', '685003', '685016'], fmt='orm')
        self.assertEqual(jobs.count(), 3)
        (dm_percent, df, all_jobs_cpu_time, agg_df) = eq.ops_costs(jobs)
        self.assertEqual(dm_percent, 43.157, 'wrong dm percent')
        self.assertEqual(df.shape, (17, 30))
        self.assertEqual(all_jobs_cpu_time, 633756327.0, 'wrong job cpu time sum')
        self.assertEqual(agg_df.shape, (3, 4))
        self.assertEqual(list(agg_df['dm_cpu_time'].values), [69603181.0, 61358737.0, 142548435.0])
        self.assertEqual(list(agg_df['dm_cpu_time%'].values), [62.0, 66.0, 33])
        self.assertEqual(list(agg_df['jobid'].values), ['685000', '685003', '685016'])
        self.assertEqual(list(agg_df['job_cpu_time'].values), [113135329.0, 93538033.0, 427082965.0])

    def test_status(self):
        status = eq.get_job_status('685000')
        self.assertEqual(
            status,
            {
                'exit_code': 0,
                'exit_reason': 'none',
                'script_path': '/home/Jeffrey.Durachta/ESM4/DECK/ESM4_historical_D151/gfdl.ncrc4-intel16-prod-openmp/scripts/postProcess/ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101.tags',
                'script_name': 'ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101'})

    @db_session
    def test_verify_jobs(self):
        import datetime
        j = Job['685000']
        p = eq.get_procs('685000', limit=1, fmt='orm')[0]
        proc_id = p.id
        j.start = datetime.datetime(1970, 1, 1)
        tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
        j.end = tomorrow
        p.start = datetime.datetime(1970, 1, 1)
        orm_commit()
        (ret, errs) = eq.verify_jobs(['685000'])
        self.assertFalse(ret)
        self.assertEqual(len(errs), 1)
        self.assertEqual(len(errs['685000']), 12)
        self.assertEqual(len([e for e in errs['685000'] if 'rdtsc_duration' in e]), 9)
        self.assertEqual(len([e for e in errs['685000'] if 'invalid timestamp' in e]), 3)
        self.assertEqual(len([e for e in errs['685000'] if 'in the future' in e]), 1)
        self.assertEqual(len([e for e in errs['685000'] if 'Process[{}]'.format(proc_id) in e]), 1)

    def test_version(self):
        self.assertTrue(eq.version() > (1, 0, 0))

    def test_zz_delete_jobs(self):
        n = eq.delete_jobs(['685000', '685016'])
        self.assertEqual(n, 0, 'multiple jobs deleted without "force"')

    def test_zz_delete_jobs_force_before_after_ags(self):
        # test before/after args
        ndays = (datetime.now() - datetime(2019, 6, 15, 7, 52, 4, 73965)).days
        n = eq.delete_jobs(JOBS_LIST, force=True, after=-(ndays - 1))
        self.assertEqual(n, 0)
        n = eq.delete_jobs(JOBS_LIST, force=True, after='06/16/2019 00:00')
        self.assertEqual(n, 0)
        n = eq.delete_jobs(JOBS_LIST, force=True, before='06/15/2019 00:00')
        self.assertEqual(n, 0)

    def test_zz_delete_jobs_force(self):
        self.assertEqual(eq.get_jobs(fmt='orm').count(), 3)
        n = eq.delete_jobs(['685000', '685016'], force=True, remove_models=True)
        self.assertEqual(n, 2)
        # self.assertFalse(eq.orm_get(eq.Job, '685000') or eq.orm_get(eq.Job, '685016'))
        # n = eq.delete_jobs([], force=True, before=-(ndays-1))
        # self.assertTrue(n >= 1)


# if __name__ == '__main__':
#    unittest.main()
#    suite = unittest.TestLoader().loadTestsFromTestCase(QueryAPI)
#    unittest.TextTestRunner(verbosity=2).run(suite)
