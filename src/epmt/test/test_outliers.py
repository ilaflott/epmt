#!/usr/bin/env python

# the import below is crucial to get a sane test environment
import unittest
from json import dumps
from epmt.orm import setup_db, db_session
from epmt.epmtlib import frozen_dict, timing
import epmt.epmt_settings as settings
import epmt.epmt_query as eq
# from json import loads
import epmt.epmt_outliers as eod
from epmt.epmtlib import frozen_dict
from json import dumps


def do_cleanup():
    eq.delete_jobs(['kern-6656-20190614-190245', 'kern-6656-20190614-191138',
                    'kern-6656-20190614-192044-outlier', 'kern-6656-20190614-194024'],
                   force=True, remove_models=True)


@timing
def setUpModule():
    #    print('\n' + str(settings.db_params))
    setup_db(settings)
    do_cleanup()
    datafiles = '{}/test/data/outliers/*.tgz'.format(install_root)
#    print('setUpModule: importing {0}'.format(datafiles))
    environ['EPMT_TZ'] = 'Asia/Kolkata'
    with capture() as (out, err):
        epmt_submit(glob(datafiles), dry_run=False)
    # only use madz for outlier detection by default
    settings.univariate_classifiers = ['modified_z_score']
    # set lower madz and z-score thresholds to easily detect outliers
    settings.outlier_thresholds['modified_z_score'] = 2.5
    settings.outlier_thresholds['z_score'] = 1.5


def tearDownModule():
    do_cleanup()


class OutliersAPI(unittest.TestCase):
    # called ONCE before before first test in this class starts
    # @classmethod
    # def setUpClass(cls):
    # pass
    ##
    # called ONCE after last tests in this class is finished
    # @classmethod
    # def tearDownClass(cls):
    # pass
    ##
    # called before every test
    # def setUp(self):
    # pass
    ##
    # called after every test
    # def tearDown(self):
    # pass

    @db_session
    def test_feature_distributions(self):
        jobs = eq.get_jobs(tags='exp_name:linux_kernel', fmt='terse')
        fdist = eod.get_feature_distributions(jobs, features=[])
        self.assertEqual(list(zip(fdist.keys(), fdist.values())),
                         [('PERF_COUNT_SW_CPU_CLOCK', 'unknown'), ('cancelled_write_bytes', 'unknown'), ('cpu_time', 'unknown'),
                          ('delayacct_blkio_time', 'unknown'), ('duration', 'unknown'), ('exitcode', 'unknown'),
                          ('guest_time', 'unknown'), ('inblock', 'norm'), ('invol_ctxsw', 'unknown'),
                          ('majflt', 'unknown'), ('minflt', 'norm'), ('num_procs', 'unknown'),
                          ('num_threads', 'unknown'), ('outblock', 'unknown'), ('processor', 'unknown'),
                          ('rchar', 'norm'), ('rdtsc_duration', 'unknown'), ('read_bytes', 'norm'),
                          ('rssmax', 'norm'), ('syscr', 'norm'), ('syscw', 'norm'),
                          ('systemtime', 'unknown'), ('time_oncpu', 'unknown'), ('time_waiting', 'unknown'),
                          ('timeslices', 'unknown'), ('usertime', 'unknown'), ('vol_ctxsw', 'norm'), ('wchar', 'norm'), ('write_bytes', 'norm')])

    @db_session
    def test_outlier_jobs(self):
        # with too few jobs and no trained model, outlier detection should fail
        too_few_jobs = eq.get_jobs(tags='exp_name:linux_kernel', fmt='terse')[:3]
        with self.assertRaises(RuntimeError):
            eod.detect_outlier_jobs(too_few_jobs)

        jobs = eq.get_jobs(tags='exp_name:linux_kernel', fmt='orm')
        (df, parts) = eod.detect_outlier_jobs(jobs)
        self.assertEqual(len(df[df.duration > 0]), 1)
        self.assertEqual(len(df[df.cpu_time > 0]), 1)
        self.assertEqual(len(df[df.num_procs > 0]), 0)
        self.assertTrue('outlier' in df[df.duration > 0]['jobid'].values[0], "wrong duration outlier")
        self.assertTrue('outlier' in df[df.cpu_time > 0]['jobid'].values[0], "wrong cpu_time outlier")
        self.assertEqual(len(parts), 3, "wrong number of items in partition dictionary")
        self.assertEqual(parts['duration'],
                         (set(['kern-6656-20190614-190245', 'kern-6656-20190614-194024', 'kern-6656-20190614-191138']),
                          set(['kern-6656-20190614-192044-outlier'])))
        # now test with wildcard features
        (df, _) = eod.detect_outlier_jobs(jobs, features='*')
        self.assertEqual(df.shape, (4, 30))
        self.assertEqual(sum(list(df.iloc[0].values)[1:]), 0)  # not an outlier by any feature
        self.assertEqual(sum(list(df.iloc[1].values)[1:]), 0)  # not an outlier by any feature
        self.assertEqual(sum(list(df.iloc[2].values)[1:]), 11)  # 11 features marked this as an outlier
        self.assertEqual(sum(list(df.iloc[3].values)[1:]), 0)  # not an outlier by any feature

    @db_session
    def test_outlier_jobs_multimode(self):
        import epmt.epmt_stat as es
        df, parts = eod.detect_outlier_jobs(
            ['kern-6656-20190614-190245',
             'kern-6656-20190614-191138',
             'kern-6656-20190614-192044-outlier',
             'kern-6656-20190614-194024'],
            methods=[es.iqr, es.modified_z_score, es.z_score])
        self.assertEqual(df.shape, (4, 4))
        self.assertEqual(set(zip(df.jobid.values, df.cpu_time.values, df.duration.values, df.num_procs.values)),
                         {('kern-6656-20190614-190245', 0, 0, 0), ('kern-6656-20190614-192044-outlier', 3, 3, 0),
                          ('kern-6656-20190614-194024', 0, 0, 0), ('kern-6656-20190614-191138', 0, 0, 0)})
        self.assertEqual(parts,
                         {'cpu_time': ({'kern-6656-20190614-190245',
                                        'kern-6656-20190614-191138',
                                        'kern-6656-20190614-194024'},
                                       {'kern-6656-20190614-192044-outlier'}),
                             'duration': ({'kern-6656-20190614-190245',
                                           'kern-6656-20190614-191138',
                                           'kern-6656-20190614-194024'},
                                          {'kern-6656-20190614-192044-outlier'}),
                             'num_procs': ({'kern-6656-20190614-190245',
                                            'kern-6656-20190614-191138',
                                            'kern-6656-20190614-192044-outlier',
                                            'kern-6656-20190614-194024'},
                                           set())})

    @db_session
    def test_outlier_no_matched_tags(self):
        retval = eod.detect_outlier_ops(['kern-6656-20190614-190245', 'kern-6656-20190614-191138',
                                         'kern-6656-20190614-192044-outlier', 'kern-6656-20190614-194024'],
                                        tags=[{'op': 'missing'}])
        self.assertFalse(retval, "No matched tags returned non False")

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
        self.assertEqual(parts['duration'],
                         (set(['kern-6656-20190614-190245', 'kern-6656-20190614-194024', 'kern-6656-20190614-191138']),
                          set(['kern-6656-20190614-192044-outlier'])))
        # now create a ref model that *includes* the outlier job
        # this way it won't later be classified as a outlier
        r = eq.create_refmodel(all_jobs, fmt='terse')
        (df, parts) = eod.detect_outlier_jobs(all_jobs, trained_model=r)
        # make sure we used default the features
        self.assertEqual(set(df.columns.values) & {'cpu_time', 'duration',
                         'num_procs'}, {'cpu_time', 'duration', 'num_procs'})
        # check there are no outliers
        self.assertEqual(len(df[df.duration > 0]), 0, "incorrect count of duration outliers")
        self.assertEqual(len(df[df.cpu_time > 0]), 0, "incorrect count of cpu_time outliers")
        self.assertEqual(len(df[df.num_procs > 0]), 0, "incorrect count of num_procs outliers")
        # now let's limit the active metrics in model and make sure
        # that outlier detection only uses the features enabled
        eq.refmodel_set_active_metrics(r, ['duration', 'cpu_time'])
        (df, _) = eod.detect_outlier_jobs(all_jobs, trained_model=r)
        self.assertEqual(set(df.columns.values) & {'cpu_time', 'duration', 'num_procs'}, {'cpu_time', 'duration'})
        # wildcard features
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
        r = eq.create_refmodel(all_jobs, features='*', fmt='terse')
        (df, _) = eod.detect_outlier_jobs(all_jobs, trained_model=r)
        # since we called eod.detect_outlier_jobs without wildcard features
        # the EOD will use the default features
        self.assertEqual(set(df.columns.values) & all_features, {'cpu_time', 'duration', 'num_procs'})
        # now let's use wildcard in the outlier detection
        (df, _) = eod.detect_outlier_jobs(all_jobs, features='*', trained_model=r)
        # now check that we used *all* the features
        self.assertEqual(set(df.columns.values) & all_features, all_features)
        #
        # let's test using IQR and z-score
        import epmt.epmt_stat as es
        for m in [es.iqr, es.z_score]:
            r = eq.create_refmodel(['kern-6656-20190614-190245', 'kern-6656-20190614-191138', 'kern-6656-20190614-194024'],
                                   methods = [m], fmt='orm')
            df, _ = eod.detect_outlier_jobs(['kern-6656-20190614-190245', 'kern-6656-20190614-191138',
                                             'kern-6656-20190614-192044-outlier', 'kern-6656-20190614-194024'],
                                            methods = [m], trained_model=r.id)
            self.assertEqual(df.shape, (4,4))
            self.assertEqual( set(zip(df.jobid.values, df.cpu_time.values, df.duration.values, df.num_procs.values)),
                              {('kern-6656-20190614-190245', 0, 0, 0), ('kern-6656-20190614-192044-outlier', 1, 1, 0),
                               ('kern-6656-20190614-194024', 0, 0, 0), ('kern-6656-20190614-191138', 0, 0, 0)})

    @db_session
    def test_outlier_jobs_trained_mvod(self):
        from epmt.epmt_stat import mvod_classifiers
        r = eq.create_refmodel( ['kern-6656-20190614-190245', 'kern-6656-20190614-191138','kern-6656-20190614-194024'],
                                methods = mvod_classifiers(), fmt='orm' )
        (df, _) = eod.detect_outlier_jobs(
            ['kern-6656-20190614-190245', 'kern-6656-20190614-191138', 'kern-6656-20190614-192044-outlier', 'kern-6656-20190614-194024'],
            trained_model = r.id, methods = mvod_classifiers())
        df.sort_values(by=['jobid'], inplace=True)
        self.assertEqual(list(df['outlier'].values), [0, 0, 2, 0])

    @db_session
    def test_outlier_ops_trained(self):
        all_jobs = eq.get_jobs(tags='exp_name:linux_kernel', fmt='orm')
        fltr = (~Job.jobid.like('%outlier%')) if settings.orm == 'sqlalchemy' else '"outlier" not in j.jobid'
        jobs_ex_outl = eq.get_jobs(tags='exp_name:linux_kernel', fmt='orm', fltr=fltr)
        r = eq.create_refmodel(jobs_ex_outl, fmt='terse', op_tags='*')
        features = ['rssmax', 'cpu_time', 'duration', 'num_procs']
        # our trained model has only duration, cpu_time, num_procs as metrics
        # so, rssmax will be discarded
        (df, parts, scores_df, sorted_tags, sorted_features) = eod.detect_outlier_ops(
            all_jobs, trained_model=r, features=features)
        self.assertEqual(df.shape, (20, 5))
        # make sure rssmax was discarded from the features
        self.assertEqual(set(df.columns.values) & set(features), {'cpu_time', 'duration', 'num_procs'})
        # pylint: disable=unsubscriptable-object
        self.assertEqual(set(df[df.duration > 0]['jobid']), set(['kern-6656-20190614-192044-outlier']))
        self.assertEqual(set(df[df.cpu_time > 0]['jobid']), set(['kern-6656-20190614-192044-outlier']))
        self.assertEqual(set(df[df.num_procs > 0]['jobid']), set([]))
        df_cols = list(df.columns)
        self.assertEqual(set(sorted_features), {'cpu_time', 'duration', 'num_procs'})
        # ensure feature order is right
        self.assertEqual(sorted_features, ['cpu_time', 'duration', 'num_procs'])
        # ensure df has the right feature order
        self.assertEqual(df_cols[2:], sorted_features)
        # esnure scores_df has the right order
        self.assertEqual(list(scores_df.columns)[1:], sorted_features)

        # ensure tag importance order is correct
        self.assertEqual(sorted_tags,
                         [{'op_instance': '5', 'op_sequence': '5', 'op': 'clean'},
                          {'op_instance': '4', 'op_sequence': '4', 'op': 'build'},
                          {'op_instance': '3', 'op_sequence': '3', 'op': 'configure'},
                          {'op_instance': '2', 'op_sequence': '2', 'op': 'extract'},
                          {'op_instance': '1', 'op_sequence': '1', 'op': 'download'}])
        # check scores_df[tags] is ordered right
        self.assertEqual([loads(t) for t in list(scores_df['tags'])], sorted_tags)
        # check df[tags] is ordered right
        uniq_tags = []
        for t in list(df['tags']):
            if t not in uniq_tags:
                uniq_tags.append(t)
        self.assertEqual(uniq_tags, sorted_tags)

        parts = {frozen_dict(loads(k)): v for k, v in parts.items()}
        self.assertEqual(parts[frozen_dict({"op_instance": "4", "op_sequence": "4", "op": "build"})], (set(
            ['kern-6656-20190614-194024', 'kern-6656-20190614-190245', 'kern-6656-20190614-191138']), set(['kern-6656-20190614-192044-outlier'])))

        # now also use the outlier job while creating the refmodel
        # this way, there should be NO outlier ops
        r = eq.create_refmodel(all_jobs, fmt='terse', op_tags='*')
        (df, parts, _, _, _) = eod.detect_outlier_ops(all_jobs, trained_model=r)
        self.assertEqual(len(df.query('duration > 0 | cpu_time > 0 | num_procs > 0')), 0)

        # now let's try creating a refmodel with a specific op_tag
        # we will get a warning in this test as the full jobs set has a different
        # set of unique process tags than the ref jobs set
        r = eq.create_refmodel(jobs_ex_outl, fmt='terse', op_tags='op_instance:4;op_sequence:4;op:build')
        (df, parts, _, _, _) = eod.detect_outlier_ops(all_jobs, trained_model=r)
        self.assertEqual(df.shape, (4, 5))
        self.assertEqual(len(parts), 1)
        parts = {frozen_dict(loads(k)): v for k, v in parts.items()}
        self.assertEqual(parts[frozen_dict({"op_instance": "4", "op_sequence": "4", "op": "build"})], (set(
            ['kern-6656-20190614-194024', 'kern-6656-20190614-190245', 'kern-6656-20190614-191138']), set(['kern-6656-20190614-192044-outlier'])))

    @db_session
    def test_outlier_ops_trained_mvod(self):
        from epmt.epmt_stat import mvod_classifiers
        jobs = eq.get_jobs(tags='exp_name:linux_kernel', fmt='terse')
        model_jobs = [ j for j in jobs if not 'outlier' in j ]
        self.assertEqual(set(model_jobs), set(['kern-6656-20190614-190245', 'kern-6656-20190614-191138', 'kern-6656-20190614-194024']))
        r = eq.create_refmodel(model_jobs, op_tags='*', methods = mvod_classifiers(), fmt='orm')
        self.assertEqual(set([j.jobid for j in r.jobs]), set(model_jobs))
        df, part = eod.detect_outlier_ops(jobs, methods = mvod_classifiers(), trained_model = r.id)
        self.assertEqual(df.shape, (20, 3))
        outliers = df[df.outlier > 0]
        self.assertEqual(outliers.shape, (5, 3))
        # only the outlier jobid is found in the outliers df
        self.assertEqual(set(outliers.jobid.values), {'kern-6656-20190614-192044-outlier'})
        self.assertEqual(list(outliers.outlier.values), [2, 2, 2, 2, 2])
        self.assertEqual(set([ dumps(x) for x in outliers.tags.values ]),
                         {'{"op": "build", "op_instance": "4", "op_sequence": "4"}',
                          '{"op": "clean", "op_instance": "5", "op_sequence": "5"}',
                          '{"op": "configure", "op_instance": "3", "op_sequence": "3"}',
                          '{"op": "download", "op_instance": "1", "op_sequence": "1"}',
                          '{"op": "extract", "op_instance": "2", "op_sequence": "2"}'})
        self.assertEqual(part,
                         {'{"op": "build", "op_instance": "4", "op_sequence": "4"}':
                          {'pyod.models.cof': [0, 0, 1, 0], 'pyod.models.hbos': [0, 0, 1, 0], 'pyod.models.ocsvm': [0, 0, 0, 0]},
                          '{"op": "clean", "op_instance": "5", "op_sequence": "5"}':
                          {'pyod.models.cof': [0, 0, 1, 0], 'pyod.models.hbos': [0, 0, 1, 0], 'pyod.models.ocsvm': [0, 0, 0, 0]},
                          '{"op": "configure", "op_instance": "3", "op_sequence": "3"}':
                          {'pyod.models.cof': [0, 0, 1, 0], 'pyod.models.hbos': [0, 0, 1, 0], 'pyod.models.ocsvm': [0, 0, 0, 0]},
                          '{"op": "download", "op_instance": "1", "op_sequence": "1"}':
                          {'pyod.models.cof': [0, 0, 1, 0], 'pyod.models.hbos': [0, 0, 1, 0], 'pyod.models.ocsvm': [0, 0, 0, 0]},
                          '{"op": "extract", "op_instance": "2", "op_sequence": "2"}':
                          {'pyod.models.cof': [0, 0, 1, 0], 'pyod.models.hbos': [0, 0, 1, 0], 'pyod.models.ocsvm': [0, 0, 0, 0]}})

    @db_session
    def test_outlier_ops(self):
        # with too few jobs and no trained model, outlier detection should fail
        too_few_jobs = eq.get_jobs(tags='exp_name:linux_kernel', fmt='terse')[:3]
        with self.assertRaises(RuntimeError):
            eod.detect_outlier_ops(too_few_jobs)

        jobs = eq.get_jobs(tags='exp_name:linux_kernel', fmt='orm')
        (df, parts, _, _, _) = eod.detect_outlier_ops(jobs)
        self.assertEqual(df.shape, (20, 5), "wrong shape of df from detect_outlier_ops")
        # pylint: disable=unsubscriptable-object
        self.assertEqual(len(df[df.duration > 0]), 3, 'wrong outlier count for duration')
        self.assertEqual(len(df[df.cpu_time > 0]), 5, 'wrong outlier count for cpu_time')
        self.assertEqual(len(df[df.num_procs > 0]), 0, 'wrong outlier count for num_procs')
        self.assertEqual(list(df.loc[2].values), ['kern-6656-20190614-192044-outlier',
                         {'op_instance': '4', 'op_sequence': '4', 'op': 'build'}, 1, 1, 0])
        self.assertEqual(len(parts), 5, 'wrong number of distinct tags')
        # print(parts.keys())
        parts = {frozen_dict(loads(k)): v for k, v in parts.items()}
        self.assertEqual(parts[frozen_dict({"op_instance": "4", "op_sequence": "4", "op": "build"})],
                         (set(['kern-6656-20190614-190245', 'kern-6656-20190614-191138', 'kern-6656-20190614-194024']),
                          set(['kern-6656-20190614-192044-outlier'])))

        (df, parts, _, _, _) = eod.detect_outlier_ops(jobs, tags={
            "op_instance": "4", "op_sequence": "4", "op": "build"})
        self.assertEqual(df.shape, (4, 5), "wrong shape of df from detect_outlier_ops with supplied tag")
        self.assertEqual(list(df.duration), [0, 0, 1, 0])
        self.assertEqual(list(df.cpu_time), [0, 0, 1, 0])
        self.assertEqual(list(df.num_procs), [0, 0, 0, 0])
        self.assertEqual(len(parts), 1)
        parts = {frozen_dict(loads(k)): v for k, v in parts.items()}
        self.assertEqual(parts[frozen_dict({"op_instance": "4", "op_sequence": "4", "op": "build"})],
                         (set(['kern-6656-20190614-190245', 'kern-6656-20190614-191138', 'kern-6656-20190614-194024']),
                          set(['kern-6656-20190614-192044-outlier'])))

        # wildcard features
        (df, _, _, _, _) = eod.detect_outlier_ops(jobs, features='*')
        self.assertEqual(df.shape, (20, 30))
        # for each op compute number of features indicating it's an outlier
        # and then test the result array
        self.assertEqual([df.iloc[i].values[2:].sum() for i in range(0, 20)], [
                         1, 0, 11, 0, 0, 1, 11, 0, 0, 0, 12, 0, 0, 1, 6, 0, 0, 2, 7, 0])

    @db_session
    def test_ops_refmodel_mvod(self):
        from epmt.epmt_stat import mvod_classifiers
        with capture() as (out, err):
            r = eq.create_refmodel( ['kern-6656-20190614-190245', 'kern-6656-20190614-191138', 'kern-6656-20190614-194024'],
                                    op_tags = [{'op': 'build'}, {'op': 'configure'}], features = ['cpu_time', 'num_procs', 'duration'],
                                    methods = mvod_classifiers(), fmt='orm')
        self.assertEqual(r.op_tags,
                         [{'op': 'build'}, {'op': 'configure'}])
        self.assertEqual(set([j.jobid for j in r.jobs]),
                         {'kern-6656-20190614-190245', 'kern-6656-20190614-194024', 'kern-6656-20190614-191138'})
        self.assertEqual(set(r.computed.keys()),
                         {'{"op": "configure"}', '{"op": "build"}'})
        scores = { k: v['cpu_time,duration,num_procs'][0] for (k,v) in r.computed['{"op": "configure"}'].items() }
        self.assertEqual( scores,
                          {'pyod.models.cof': 1.3176, 'pyod.models.hbos': 9.9656, 'pyod.models.ocsvm': -0.0})
        #                  {'pyod.models.cof': 1.3176, 'pyod.models.mcd': 2.0, 'pyod.models.hbos': 9.9656, 'pyod.models.ocsvm': -0.0})
        scores = { k: v['cpu_time,duration,num_procs'][0] for (k,v) in r.computed['{"op": "build"}'].items() }
        self.assertEqual(scores,
                         {'pyod.models.cof': 1.0355, 'pyod.models.hbos': 9.9657, 'pyod.models.ocsvm': -0.0})
        #                 {'pyod.models.mcd': 2.0, 'pyod.models.cof': 1.0355, 'pyod.models.hbos': 9.9657, 'pyod.models.ocsvm': -0.0})
        self.assertEqual( r.computed['{"op": "build"}'],
                          {
                           'pyod.models.cof': {'cpu_time,duration,num_procs': [1.0355,
                                                                               [[380807266.0, 2158730624.0, 9549.0],
                                                                                [381619141.0, 2203839312.0, 9549.0],
                                                                                [381227732.0, 2253935203.0, 9549.0]]]},
                           'pyod.models.hbos': {'cpu_time,duration,num_procs': [9.9657,
                                                                                [[380807266.0, 2158730624.0, 9549.0],
                                                                                 [381619141.0, 2203839312.0, 9549.0],
                                                                                 [381227732.0, 2253935203.0, 9549.0]]]},
                           'pyod.models.ocsvm': {'cpu_time,duration,num_procs': [-0.0,
                                                                                 [[380807266.0, 2158730624.0, 9549.0],
                                                                                  [381619141.0, 2203839312.0, 9549.0],
                                                                                  [381227732.0, 2253935203.0, 9549.0]]]}})        
        self.assertEqual(r.computed['{"op": "configure"}'],
                         {
                          'pyod.models.cof': {'cpu_time,duration,num_procs': [1.3176,
                                                                              [[20735346.0, 249388754.0, 1044.0],
                                                                               [20476970.0, 203959083.0, 1044.0],
                                                                               [20718776.0, 236011451.0, 1044.0]]]},
                          'pyod.models.hbos': {'cpu_time,duration,num_procs': [9.9656,
                                                                               [[20735346.0, 249388754.0, 1044.0],
                                                                                [20476970.0, 203959083.0, 1044.0],
                                                                                [20718776.0, 236011451.0, 1044.0]]]},
                          'pyod.models.ocsvm': {'cpu_time,duration,num_procs': [-0.0,
                                                                                [[20735346.0, 249388754.0, 1044.0],
                                                                                 [20476970.0, 203959083.0, 1044.0],
                                                                                 [20718776.0, 236011451.0, 1044.0]]]}})

    @db_session
    def test_detect_outliers(self):
        import numpy as np
        import pandas as pd
        import epmt.epmt_stat as es
        np.random.seed(0)
        data = np.random.randn(10, 2)
        data[5] = [2 * data[:, 0].max(), 2 * data[:, 1].max()]
        df = pd.DataFrame(data)
        outliers = eod.detect_outliers(df, methods=[es.iqr, es.modified_z_score])
        self.assertEqual(list(outliers.iloc[5].values), [2, 2])

    @db_session
    def test_outlier_processes(self):
        import epmt.epmt_stat as es
        p = eq.get_procs('kern-6656-20190614-190245', fmt='pandas', order=eq.desc(eq.Process.duration), limit=1)
        # clone and make 10 rows of the 1 process row
        procs = p.append([p] * 9, ignore_index=True)
        # now double the value of cpu_time/duration of the 6th row
        # thus making it an outlier
        procs.loc[[5], 'duration'] *= 2
        procs.loc[[5], 'cpu_time'] *= 2
        # make sure the modified row is detected as an outlier
        outliers = eod.detect_outlier_processes(procs, ['duration', 'cpu_time'], methods=[es.iqr, es.modified_z_score])
        self.assertEqual(list(outliers.loc[5].values), [2, 2])

    @db_session
    def test_outlier_threads(self):
        import epmt.epmt_stat as es
        p = eq.get_procs('kern-6656-20190614-190245', fmt='orm', order=eq.desc(eq.Process.duration), limit=1)[0]
        t = eq.get_thread_metrics(p)
        # clone and make 10 rows of the 1 thread row
        threads = t.append([t] * 9, ignore_index=True)
        # now increase the value of usertime/systemtime of the 6th row
        # thus making it an outlier
        threads.loc[[5], 'usertime'] *= 2
        threads.loc[[5], 'systemtime'] *= 2
        # make sure the modified row is detected as an outlier
        outliers = eod.detect_outlier_threads(
            threads, [
                'usertime', 'systemtime'], methods=[
                es.iqr, es.modified_z_score])
        self.assertEqual(list(outliers.loc[5].values), [2, 2])

    @db_session
    def test_partition_jobs(self):
        jobs = eq.get_jobs(tags='launch_id:6656', fmt='orm')
        self.assertEqual(jobs.count(), 4, "incorrect job count using tags")
        parts = eod.partition_jobs(jobs)
        self.assertEqual(len(parts), 3, "incorrect count of items in partition dict")
        self.assertEqual(parts['cpu_time'],
                         (set(['kern-6656-20190614-190245', 'kern-6656-20190614-194024', 'kern-6656-20190614-191138']),
                          set(['kern-6656-20190614-192044-outlier'])))
        self.assertEqual(parts['duration'],
                         (set(['kern-6656-20190614-190245', 'kern-6656-20190614-194024', 'kern-6656-20190614-191138']),
                          set(['kern-6656-20190614-192044-outlier'])))
        self.assertEqual(parts['num_procs'],
                         (set(['kern-6656-20190614-190245',
                               'kern-6656-20190614-192044-outlier',
                               'kern-6656-20190614-194024',
                               'kern-6656-20190614-191138']),
                          set([])))

    @db_session
    def test_partition_jobs_by_ops(self):
        jobs = eq.get_jobs(fmt='terse', tags='exp_name:linux_kernel')
        parts = eod.partition_jobs_by_ops(jobs)
        self.assertEqual(len(parts), 5, "incorrect number of tags in output")
        parts = {frozen_dict(loads(k)): v for k, v in parts.items()}
        self.assertEqual(parts[frozen_dict({"op_instance": "3", "op_sequence": "3", "op": "configure"})],
                         (set(['kern-6656-20190614-190245', 'kern-6656-20190614-191138', 'kern-6656-20190614-194024']),
                          set(['kern-6656-20190614-192044-outlier'])), "wrong partitioning for configure op")
        parts = eod.partition_jobs_by_ops(jobs, tags='op:build;op_instance:4;op_sequence:4')
        self.assertEqual(len(parts), 1)
        parts = {frozen_dict(loads(k)): v for k, v in parts.items()}
        self.assertEqual(parts[frozen_dict({"op_instance": "4", "op_sequence": "4", "op": "build"})],
                         (set(['kern-6656-20190614-190245', 'kern-6656-20190614-191138', 'kern-6656-20190614-194024']),
                          set(['kern-6656-20190614-192044-outlier'])), "wrong partitioning when supplying a single tag string")
        parts = eod.partition_jobs_by_ops(
            jobs, tags=[
                'op:build;op_instance:4;op_sequence:4', {
                    "op_instance": "2", "op_sequence": "2", "op": "extract"}])
        self.assertEqual(len(parts), 2)
        parts = {frozen_dict(loads(k)): v for k, v in parts.items()}
        self.assertEqual(parts[frozen_dict({"op_instance": "4", "op_sequence": "4", "op": "build"})],
                         (set(['kern-6656-20190614-190245', 'kern-6656-20190614-191138', 'kern-6656-20190614-194024']),
                          set(['kern-6656-20190614-192044-outlier'])))
        self.assertEqual(parts[frozen_dict({"op_instance": "2",
                                            "op_sequence": "2",
                                            "op": "extract"})],
                         (set(['kern-6656-20190614-190245',
                               'kern-6656-20190614-191138',
                               'kern-6656-20190614-194024']),
                          set(['kern-6656-20190614-192044-outlier'])),
                         "wrong partitioning when supplying tags consisting of a list of string and dict")

    def test_pca(self):
        jobs_df = eq.get_jobs(tags='exp_name:linux_kernel', fmt='pandas')
        (df_pca, variances, pca_features, _) = eod.pca_feature_combine(jobs_df, desired=0.80)
        self.assertEqual(pca_features, ['pca_01', 'pca_02'])
        self.assertEqual([round(v, 4) for v in list(variances)], [0.6811, 0.2458])
        (df_outl, _) = eod.detect_outlier_jobs(df_pca, features=pca_features)
        df_outl = df_outl.sort_values('jobid')
        self.assertEqual(df_outl.shape, (4, 3))
        self.assertEqual(list(df_outl['jobid'].values),
                         ['kern-6656-20190614-190245',
                          'kern-6656-20190614-191138',
                          'kern-6656-20190614-192044-outlier',
                          'kern-6656-20190614-194024'])
        self.assertEqual(list(df_outl['pca_01'].values), [0, 0, 1, 0])
        self.assertEqual(list(df_outl['pca_02'].values), [0, 0, 0, 0])
        # now lets get the weighted pca scores
        (pca_weighted_df, pca_weighted_vec) = eod._pca_weighted_score(df_outl, pca_features, variances)
        self.assertEqual(list(pca_weighted_vec), [0.0, 0.0, 2.8, 0.0])
        self.assertEqual(pca_weighted_df.shape, (4, 4))
        self.assertEqual(list(pca_weighted_df['pca_weighted'].values), [0.0, 0.0, 2.8, 0.0])

        # now try with single PCA component
        (df, variances, pca_features, _) = eod.pca_feature_combine(jobs_df, desired=1)
        self.assertEqual([round(v, 4) for v in list(variances)], [0.6811])
        self.assertEqual(pca_features, ['pca_01'])
        (outl, _) = eod.detect_outlier_jobs(df, features=pca_features)
        outl = outl.sort_values('jobid')
        self.assertEqual(outl.shape, (4, 2))
        self.assertEqual(list(outl['jobid'].values),
                         ['kern-6656-20190614-190245',
                          'kern-6656-20190614-191138',
                          'kern-6656-20190614-192044-outlier',
                          'kern-6656-20190614-194024'])
        self.assertEqual(list(outl['pca_01'].values), [0, 0, 1, 0])

        # now let's use the detect_outlier_jobs call with pca enabled
        # we now will have an extra column with weighted PCA outlier scores
        (outl, _) = eod.detect_outlier_jobs(jobs_df, features=[], pca=True)
        outl = outl.sort_values('jobid')
        self.assertEqual(outl.shape, (4, 4))
        self.assertEqual(list(outl['jobid'].values),
                         ['kern-6656-20190614-190245',
                          'kern-6656-20190614-191138',
                          'kern-6656-20190614-192044-outlier',
                          'kern-6656-20190614-194024'])
        self.assertEqual(list(outl['pca_weighted'].values), [0.0, 0.0, 2.8, 0.0])
        self.assertEqual(list(outl['pca_01'].values), [0, 0, 1, 0])
        self.assertEqual(list(outl['pca_02'].values), [0, 0, 0, 0])

    def test_pca_feature_rank(self):
        jobs_df = eq.get_jobs(tags='exp_name:linux_kernel', fmt='pandas')
        (_, _, _, features_df) = eod.pca_feature_combine(jobs_df)
        self.assertEqual(features_df.shape, (2, 29))
        # check the first row of the dataframe
        self.assertEqual(set(zip(abs(features_df).iloc[0].index.values, abs(features_df).iloc[0].values.round(4))),
                         {('duration', 0.2618), ('time_oncpu', 0.2612), ('outblock', 0.0), ('systemtime', 0.2621), ('syscr', 0.2351),
                          ('cancelled_write_bytes', 0.261), ('syscw', 0.2166), ('rssmax',
                                                                                0.2392), ('processor', 0.0), ('exitcode', 0.0),
                          ('wchar', 0.0813), ('time_waiting', 0.2619), ('majflt',
                                                                        0.0), ('cpu_time', 0.2612), ('num_procs', 0.0),
                          ('rdtsc_duration', 0.2612), ('invol_ctxsw', 0.2605), ('inblock',
                                                                                0.1209), ('PERF_COUNT_SW_CPU_CLOCK', 0.2612),
                          ('minflt', 0.0422), ('guest_time', 0.0), ('num_threads',
                                                                    0.0), ('vol_ctxsw', 0.2265), ('usertime', 0.261),
                          ('write_bytes', 0.0822), ('timeslices', 0.2594), ('rchar', 0.061), ('delayacct_blkio_time', 0.0), ('read_bytes', 0.0758)})
        # check the second row of the dataframe
        self.assertEqual(set(zip(abs(features_df).iloc[1].index.values, abs(features_df).iloc[1].values.round(4))),
                         {('duration', 0.062), ('time_waiting', 0.0575), ('outblock', 0.0), ('vol_ctxsw', 0.0195), ('syscw', 0.1484),
                          ('usertime', 0.0693), ('rssmax', 0.1546), ('time_oncpu',
                                                                     0.0671), ('processor', 0.0), ('exitcode', 0.0),
                          ('read_bytes', 0.4215), ('majflt', 0.0), ('num_procs',
                                                                    0.0), ('rdtsc_duration', 0.0685), ('syscr', 0.005),
                          ('systemtime', 0.0572), ('cancelled_write_bytes',
                                                   0.0688), ('wchar', 0.4183), ('num_threads', 0.0),
                          ('guest_time', 0.0), ('write_bytes', 0.4179), ('cpu_time',
                                                                         0.0672), ('timeslices', 0.0796), ('rchar', 0.4092),
                          ('invol_ctxsw', 0.074), ('inblock', 0.3839), ('PERF_COUNT_SW_CPU_CLOCK',
                                                                        0.0669), ('delayacct_blkio_time', 0.0),
                          ('minflt', 0.2482)})

        # Now let's use the function designed to rank features
        df, sorted_features = eod.pca_feature_rank(jobs_df)
        self.assertEqual(df.shape, (3, 29))
        self.assertEqual(list(df.columns.values),
                         ['rssmax', 'timeslices', 'invol_ctxsw', 'usertime', 'rdtsc_duration', 'cancelled_write_bytes', 'cpu_time', 'time_oncpu',
                          'PERF_COUNT_SW_CPU_CLOCK', 'duration', 'systemtime', 'time_waiting', 'syscw', 'inblock', 'syscr', 'vol_ctxsw', 'write_bytes',
                          'wchar', 'read_bytes', 'rchar', 'minflt', 'outblock', 'num_threads', 'num_procs', 'majflt', 'guest_time', 'exitcode',
                          'delayacct_blkio_time', 'processor'])
        self.assertEqual(list(df.iloc[0].values),
                         [0.2392, 0.2594, 0.2605, 0.261, 0.2612, -0.261, 0.2612, 0.2612, 0.2612, 0.2618, 0.2621, 0.2619, 0.2166, -0.1209, -0.2351,
                          -0.2265, -0.0822, -0.0813, -0.0758, -0.061, 0.0422, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        self.assertEqual(list(df.iloc[1].values),
                         [-0.1546, 0.0796, 0.074, 0.0693, 0.0685, -0.0688, 0.0672, 0.0671, 0.0669, 0.062, 0.0572, 0.0575, 0.1484, 0.3839,
                          0.005, 0.0195, 0.4179, 0.4183, 0.4215, 0.4092, -0.2482, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        self.assertEqual(list(df.iloc[-1].values),
                         [0.2168, 0.2117, 0.211, 0.2101, 0.2101, 0.21, 0.2097, 0.2097, 0.2097, 0.2088, 0.2077, 0.2077, 0.1985, 0.1906,
                          0.1741, 0.1716, 0.1713, 0.1707, 0.1675, 0.1534, 0.0968, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        self.assertEqual(sorted_features,
                         [('rssmax', 0.2168), ('timeslices', 0.2117), ('invol_ctxsw', 0.211), ('usertime', 0.2101), ('rdtsc_duration', 0.2101),
                          ('cancelled_write_bytes', 0.21), ('cpu_time', 0.2097), ('time_oncpu', 0.2097), ('PERF_COUNT_SW_CPU_CLOCK', 0.2097),
                          ('duration', 0.2088), ('systemtime', 0.2077), ('time_waiting', 0.2077), ('syscw', 0.1985), ('inblock', 0.1906),
                          ('syscr', 0.1741), ('vol_ctxsw', 0.1716), ('write_bytes', 0.1713), ('wchar', 0.1707), ('read_bytes', 0.1675), ('rchar', 0.1534),
                          ('minflt', 0.0968), ('outblock', 0.0), ('num_threads', 0.0), ('num_procs', 0.0), ('majflt', 0.0), ('guest_time', 0.0), ('exitcode', 0.0),
                          ('delayacct_blkio_time', 0.0), ('processor', 0.0)])

    def test_pca_ops(self):
        out_df = eod.detect_outlier_ops(['kern-6656-20190614-190245',
                                         'kern-6656-20190614-191138',
                                         'kern-6656-20190614-192044-outlier',
                                         'kern-6656-20190614-194024'],
                                        features=[],
                                        pca=True)
        self.assertEqual(out_df.shape, (20, 5))
        self.assertEqual(out_df[out_df.pca_weighted > 0].shape, (5, 5))
        self.assertEqual(set(out_df[out_df.pca_weighted > 0].jobid.values), {'kern-6656-20190614-192044-outlier'})
        self.assertEqual(list(out_df[out_df.pca_weighted > 0].pca_weighted.values), [3.8, 3.8, 3.8, 3.8, 3.8])
        self.assertEqual(list(out_df[out_df.pca_weighted > 0].pca_weighted.index.values), [2, 6, 10, 14, 18])

    def test_pca_trained_model(self):
        r = eq.create_refmodel(['kern-6656-20190614-190245', 'kern-6656-20190614-191138', 'kern-6656-20190614-194024'], features=[], pca=True, fmt='orm')
        self.assertEqual([j.jobid for j in r.jobs],
                         ['kern-6656-20190614-190245', 'kern-6656-20190614-191138', 'kern-6656-20190614-194024'])
        self.assertEqual(r.info_dict['pca']['inp_features'],
                         ['PERF_COUNT_SW_CPU_CLOCK', 'cancelled_write_bytes', 'cpu_time', 'delayacct_blkio_time',
                          'duration', 'exitcode', 'guest_time', 'inblock', 'invol_ctxsw', 'majflt', 'minflt',
                          'num_procs', 'num_threads', 'outblock', 'processor', 'rchar', 'rdtsc_duration', 'read_bytes',
                          'rssmax', 'syscr', 'syscw', 'systemtime', 'time_oncpu', 'time_waiting', 'timeslices',
                          'usertime', 'vol_ctxsw', 'wchar', 'write_bytes'])
        self.assertEqual(r.info_dict['pca']['out_features'], ['pca_01', 'pca_02'])
        self.assertEqual(list(r.computed['modified_z_score'].keys()), ['pca_01', 'pca_02'])
        (df, part) = eod.detect_outlier_jobs(['kern-6656-20190614-190245', 'kern-6656-20190614-191138', 'kern-6656-20190614-192044-outlier'],
                                             trained_model = r.id, features = [], pca=True)
        self.assertEqual(df.shape, (3, 4))
        self.assertEqual(list(df.columns), ['jobid', 'pca_weighted', 'pca_01', 'pca_02'])
        self.assertEqual(set(df.jobid.values),
                         {'kern-6656-20190614-191138',
                          'kern-6656-20190614-192044-outlier',
                          'kern-6656-20190614-190245'})
        self.assertEqual(df[df.jobid == 'kern-6656-20190614-192044-outlier'].shape, (1, 4))
        self.assertEqual(list(df[df.jobid == 'kern-6656-20190614-192044-outlier'].iloc[0].values),
                         ['kern-6656-20190614-192044-outlier', 2.8, 1, 0])
        self.assertEqual(df[df.jobid != 'kern-6656-20190614-192044-outlier'].shape, (2, 4))
        self.assertEqual(df[df.jobid != 'kern-6656-20190614-192044-outlier']['pca_weighted'].sum(), 0.0)

    def test_pca_trained_model_ops(self):
        r = eq.create_refmodel(['kern-6656-20190614-190245', 'kern-6656-20190614-191138', 'kern-6656-20190614-194024'], op_tags='*', features=[], pca=True, fmt='orm')
        self.assertEqual( [j.jobid for j in r.jobs],
                          ['kern-6656-20190614-190245', 'kern-6656-20190614-191138', 'kern-6656-20190614-194024'])
        self.assertEqual( r.info_dict['pca']['inp_features'],
                          ['PERF_COUNT_SW_CPU_CLOCK', 'cancelled_write_bytes', 'cpu_time', 'delayacct_blkio_time',
                           'duration', 'exitcode', 'guest_time', 'inblock', 'invol_ctxsw', 'majflt', 'minflt',
                           'num_procs', 'num_threads', 'outblock', 'processor', 'rchar', 'rdtsc_duration', 'read_bytes',
                           'rssmax', 'syscr', 'syscw', 'systemtime', 'time_oncpu', 'time_waiting', 'timeslices', 'usertime',
                           'vol_ctxsw', 'wchar', 'write_bytes'])
        self.assertEqual(r.info_dict['pca']['out_features'],
                         ['pca_01', 'pca_02'])
        self.assertEqual(set(r.computed.keys()),
                         {'{"op": "configure", "op_instance": "3", "op_sequence": "3"}',
                          '{"op": "download", "op_instance": "1", "op_sequence": "1"}',
                          '{"op": "clean", "op_instance": "5", "op_sequence": "5"}',
                          '{"op": "extract", "op_instance": "2", "op_sequence": "2"}',
                          '{"op": "build", "op_instance": "4", "op_sequence": "4"}'})
        self.assertEqual(r.computed,
                         {'{"op": "build", "op_instance": "4", "op_sequence": "4"}': {'modified_z_score': {'pca_01': (1.5029, 8.0231, 0.0884),
                                                                                                           'pca_02': (4.8231, -0.2834, 0.0237)}},
                          '{"op": "clean", "op_instance": "5", "op_sequence": "5"}': {'modified_z_score': {'pca_01': (2.1959, -2.4257, 0.0036),
                                                                                                           'pca_02': (1.6775, -2.1972, 0.0033)}},
                          '{"op": "configure", "op_instance": "3", "op_sequence": "3"}': {'modified_z_score': {'pca_01': (1.355, -1.6145, 0.0304),
                                                                                                               'pca_02': (1.1647, -1.5633, 0.0194)}},
                          '{"op": "download", "op_instance": "1", "op_sequence": "1"}': {'modified_z_score': {'pca_01': (2.2482, -2.4305, 0.0005),
                                                                                                              'pca_02': (0.9081, -0.9759, 0.0013)}},
                          '{"op": "extract", "op_instance": "2", "op_sequence": "2"}': {'modified_z_score': {'pca_01': (1.7217, -1.5568, 0.1045),
                                                                                                             'pca_02': (0.7617, 5.0688, 0.0796)}}})
        df = eod.detect_outlier_ops(['kern-6656-20190614-190245', 'kern-6656-20190614-192044-outlier'], trained_model=r.id, features=[], pca = True)
        self.assertEqual(df.shape, (10, 5))
        self.assertEqual(set(df.jobid.values), {'kern-6656-20190614-190245', 'kern-6656-20190614-192044-outlier'})
        # kern-6656-20190614-190245 is never an outlier
        self.assertEqual(df[df.jobid == 'kern-6656-20190614-190245']['pca_weighted'].sum(), 0.0)
        self.assertEqual(list(df[df.jobid == 'kern-6656-20190614-192044-outlier']
                         ['pca_weighted'].values), [3.6, 3.6, 3.6, 3.6, 3.6])
        self.assertEqual(list(df[df.jobid == 'kern-6656-20190614-192044-outlier']['pca_01'].values), [1, 1, 1, 1, 1])
        self.assertEqual(list(df[df.jobid == 'kern-6656-20190614-192044-outlier']['pca_02'].values), [1, 1, 1, 1, 1])
        tags = list(df.tags.values)
        from epmt.epmtlib import frozen_dict
        tags = [frozen_dict(t) for t in tags]
        self.assertEqual(set(tags),
                         {frozenset({('op', 'configure'), ('op_sequence', '3'), ('op_instance', '3')}),
                          frozenset({('op', 'download'), ('op_sequence', '1'), ('op_instance', '1')}),
                          frozenset({('op_sequence', '4'), ('op_instance', '4'), ('op', 'build')}),
                          frozenset({('op_sequence', '5'), ('op_instance', '5'), ('op', 'clean')}),
                          frozenset({('op', 'extract'), ('op_sequence', '2'), ('op_instance', '2')})})

    def test_feature_scatter_plot_no_static(self):
        from tempfile import NamedTemporaryFile, gettempdir
        plotfile = NamedTemporaryFile(prefix='output_', suffix='.png', dir=gettempdir())
        plotfile = plotfile.name
        jobs = [
            'kern-6656-20190614-190245',
            'kern-6656-20190614-191138',
            'kern-6656-20190614-192044-outlier',
            'kern-6656-20190614-194024']
        with capture() as (out, err):
            figure = eod.feature_scatter_plot(jobs, outfile=plotfile)
        s = out.getvalue()
        self.assertIn('Plotly Cannot export static images, Feature coming soon', s)

    def test_feature_scatter_plot_names(self):
        from tempfile import NamedTemporaryFile, gettempdir
        plotfile = NamedTemporaryFile(prefix='output_', suffix='.png', dir=gettempdir())
        plotfile = plotfile.name
        jobs = [
            'kern-6656-20190614-190245',
            'kern-6656-20190614-191138',
            'kern-6656-20190614-192044-outlier',
            'kern-6656-20190614-194024']
        figure = eod.feature_scatter_plot(jobs)
        jobs_in_figure = [point['name'] for point in figure.data]
        self.assertEqual(set(jobs), set(jobs_in_figure))

    @db_session
    def test_rca_jobs(self):
        fltr = (~Job.jobid.like('%outlier%')) if settings.orm == 'sqlalchemy' else '"outlier" not in j.jobid'
        ref_jobs = eq.get_jobs(tags='exp_name:linux_kernel', fmt='orm', fltr=fltr)
        fltr2 = (Job.jobid.like('%outlier%')) if settings.orm == 'sqlalchemy' else '"outlier" in j.jobid'
        outlier_job = eq.get_jobs(tags='exp_name:linux_kernel', fltr=fltr2, fmt='orm')
        (res, df, sl) = eod.detect_rootcause(ref_jobs, outlier_job)
        self.assertTrue(res, 'detect_rootcause returned False')
        self.assertEqual(list(df.columns.values), ['cpu_time', 'duration',
                         'num_procs'], 'wrong order of features returned by RCA')
        self.assertEqual(df.shape, (12, 3), "wrong dataframe format")
        self.assertEqual([int(x) for x in list(df.loc['modified_z_score_ratio'])],
                         [204, 27, 0], "wrong madz score ratios")

    @db_session
    def test_rca_ops(self):
        fltr = (~Job.jobid.like('%outlier%')) if settings.orm == 'sqlalchemy' else '"outlier" not in j.jobid'
        ref_jobs = eq.get_jobs(tags='exp_name:linux_kernel', fmt='orm', fltr=fltr)
        fltr2 = (Job.jobid.like('%outlier%')) if settings.orm == 'sqlalchemy' else '"outlier" in j.jobid'
        outlier_job = eq.get_jobs(tags='exp_name:linux_kernel', fltr=fltr2, fmt='orm')
        (res, df, sl) = eod.detect_rootcause_op(ref_jobs, outlier_job, tag='op_sequence:4')
        self.assertTrue(res, 'detect_rootcause_op returned False')
        self.assertEqual(list(df.columns.values), ['cpu_time', 'duration',
                         'num_procs'], 'wrong order of features returned by RCA')
        self.assertEqual(df.shape, (12, 3), "wrong dataframe format")
        self.assertEqual([int(x) for x in list(df.loc['modified_z_score_ratio'])], [379, 56, 0])

    @db_session
    def test_trained_model(self):
        fltr = (~Job.jobid.like('%outlier%')) if settings.orm == 'sqlalchemy' else '"outlier" not in j.jobid'
        jobs = eq.get_jobs(tags='exp_name:linux_kernel', fmt='orm', fltr=fltr)
        self.assertEqual(jobs.count(), 3)
        r = eq.create_refmodel(jobs, tag='exp_name:linux_kernel_test', fmt='orm')
        self.assertEqual(r.tags, {'exp_name': 'linux_kernel_test'})
        rq = eq.get_refmodels(tag='exp_name:linux_kernel_test', fmt='orm')
        self.assertEqual(rq.count(), 1)
        r1 = rq.first()
        self.assertEqual(r1.id, r.id)
        self.assertEqual(r1.tags, {'exp_name': 'linux_kernel_test'})
        self.assertFalse(r1.op_tags)
        # pony and sqlalchemy have slightly different outputs
        # in pony each value in modfied_z_score dictionary is a
        # a tuple, while in sqlalchemy it's a list. So, we use
        # assertIn to check if either match occurs
        self.assertIn(r1.computed,
                      ({'modified_z_score': {'duration': (1.0287, 542680315.0, 14860060.0),
                                             'cpu_time': (1.3207, 449914707.0, 444671.0),
                                             'num_procs': (0.0, 10600.0, 0.0)}},
                       {'modified_z_score': {'duration': [1.0287, 542680315.0, 14860060.0],
                                             'cpu_time': [1.3207, 449914707.0, 444671.0],
                                             'num_procs': [0.0, 10600.0, 0.0]}}))
        self.assertEqual(set([j.jobid for j in r1.jobs]),
                         set(['kern-6656-20190614-194024', 'kern-6656-20190614-191138', 'kern-6656-20190614-190245']))


if __name__ == '__main__':
    unittest.main()
