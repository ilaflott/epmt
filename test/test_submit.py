#!/usr/bin/env python

# the import below is crucial to get a sane test environment
from . import *


@timing
def setUpModule():
    print('\n' + str(settings.db_params))
    setup_db(settings)
    datafiles='test/data/misc/685000.tgz'
    print('setUpModule: importing {0}'.format(datafiles))
    epmt_submit(glob(datafiles), dry_run=False)
    
def tearDownModule():
    pass

class EPMTSubmit(unittest.TestCase):
    @db_session
    def test_job_data(self):
        job_dict = eq.orm_to_dict(Job['685000'])
        ref_dict = {'proc_sums': {u'majflt': 8, u'systemtime': 41980075, u'invol_ctxsw': 20900, u'inblock': 13672, u'vol_ctxsw': 770843, u'read_bytes': 7000064, u'PERF_COUNT_SW_CPU_CLOCK': 86903088007, u'cancelled_write_bytes': 8925798400, u'timeslices': 795433, u'wchar': 15066048420, u'guest_time': 0, u'rssmax': 31621528, u'num_threads': 3668, u'write_bytes': 12254015488, u'minflt': 4972187, u'rdtsc_duration': -112126610546481758, u'usertime': 71155254, u'time_oncpu': 115330986461, u'all_proc_tags': [{u'op_instance': u'11', u'op_sequence': u'66', u'op': u'cp'}, {u'op_instance': u'15', u'op_sequence': u'79', u'op': u'cp'}, {u'op_instance': u'3', u'op_sequence': u'30', u'op': u'cp'}, {u'op_instance': u'5', u'op_sequence': u'39', u'op': u'cp'}, {u'op_instance': u'7', u'op_sequence': u'48', u'op': u'cp'}, {u'op_instance': u'9', u'op_sequence': u'57', u'op': u'cp'}, {u'op_instance': u'2', u'op_sequence': u'89', u'op': u'dmput'}, {u'op_instance': u'2', u'op_sequence': u'31', u'op': u'fregrid'}, {u'op_instance': u'3', u'op_sequence': u'40', u'op': u'fregrid'}, {u'op_instance': u'4', u'op_sequence': u'49', u'op': u'fregrid'}, {u'op_instance': u'5', u'op_sequence': u'58', u'op': u'fregrid'}, {u'op_instance': u'6', u'op_sequence': u'67', u'op': u'fregrid'}, {u'op_instance': u'7', u'op_sequence': u'80', u'op': u'fregrid'}, {u'op_instance': u'1', u'op_sequence': u'1', u'op': u'hsmget'}, {u'op_instance': u'1', u'op_sequence': u'3', u'op': u'hsmget'}, {u'op_instance': u'1', u'op_sequence': u'5', u'op': u'hsmget'}, {u'op_instance': u'1', u'op_sequence': u'7', u'op': u'hsmget'}, {u'op_instance': u'1', u'op_sequence': u'9', u'op': u'hsmget'}, {u'op_instance': u'3', u'op_sequence': u'10', u'op': u'hsmget'}, {u'op_instance': u'3', u'op_sequence': u'2', u'op': u'hsmget'}, {u'op_instance': u'3', u'op_sequence': u'4', u'op': u'hsmget'}, {u'op_instance': u'3', u'op_sequence': u'6', u'op': u'hsmget'}, {u'op_instance': u'3', u'op_sequence': u'8', u'op': u'hsmget'}, {u'op_instance': u'4', u'op_sequence': u'11', u'op': u'hsmget'}, {u'op_instance': u'4', u'op_sequence': u'14', u'op': u'hsmget'}, {u'op_instance': u'4', u'op_sequence': u'17', u'op': u'hsmget'}, {u'op_instance': u'4', u'op_sequence': u'20', u'op': u'hsmget'}, {u'op_instance': u'4', u'op_sequence': u'23', u'op': u'hsmget'}, {u'op_instance': u'6', u'op_sequence': u'12', u'op': u'hsmget'}, {u'op_instance': u'6', u'op_sequence': u'15', u'op': u'hsmget'}, {u'op_instance': u'6', u'op_sequence': u'18', u'op': u'hsmget'}, {u'op_instance': u'6', u'op_sequence': u'21', u'op': u'hsmget'}, {u'op_instance': u'6', u'op_sequence': u'24', u'op': u'hsmget'}, {u'op_instance': u'7', u'op_sequence': u'13', u'op': u'hsmget'}, {u'op_instance': u'7', u'op_sequence': u'16', u'op': u'hsmget'}, {u'op_instance': u'7', u'op_sequence': u'19', u'op': u'hsmget'}, {u'op_instance': u'7', u'op_sequence': u'22', u'op': u'hsmget'}, {u'op_instance': u'7', u'op_sequence': u'25', u'op': u'hsmget'}, {u'op_instance': u'1', u'op_sequence': u'33', u'op': u'mv'}, {u'op_instance': u'10', u'op_sequence': u'60', u'op': u'mv'}, {u'op_instance': u'13', u'op_sequence': u'69', u'op': u'mv'}, {u'op_instance': u'16', u'op_sequence': u'74', u'op': u'mv'}, {u'op_instance': u'18', u'op_sequence': u'83', u'op': u'mv'}, {u'op_instance': u'18', u'op_sequence': u'86', u'op': u'mv'}, {u'op_instance': u'20', u'op_sequence': u'84', u'op': u'mv'}, {u'op_instance': u'20', u'op_sequence': u'87', u'op': u'mv'}, {u'op_instance': u'4', u'op_sequence': u'42', u'op': u'mv'}, {u'op_instance': u'7', u'op_sequence': u'51', u'op': u'mv'}, {u'op_instance': u'11', u'op_sequence': u'68', u'op': u'ncatted'}, {u'op_instance': u'12', u'op_sequence': u'73', u'op': u'ncatted'}, {u'op_instance': u'15', u'op_sequence': u'82', u'op': u'ncatted'}, {u'op_instance': u'15', u'op_sequence': u'85', u'op': u'ncatted'}, {u'op_instance': u'3', u'op_sequence': u'32', u'op': u'ncatted'}, {u'op_instance': u'5', u'op_sequence': u'41', u'op': u'ncatted'}, {u'op_instance': u'7', u'op_sequence': u'50', u'op': u'ncatted'}, {u'op_instance': u'9', u'op_sequence': u'59', u'op': u'ncatted'}, {u'op_instance': u'10', u'op_sequence': u'62', u'op': u'ncrcat'}, {u'op_instance': u'12', u'op_sequence': u'71', u'op': u'ncrcat'}, {u'op_instance': u'13', u'op_sequence': u'76', u'op': u'ncrcat'}, {u'op_instance': u'2', u'op_sequence': u'26', u'op': u'ncrcat'}, {u'op_instance': u'4', u'op_sequence': u'35', u'op': u'ncrcat'}, {u'op_instance': u'6', u'op_sequence': u'44', u'op': u'ncrcat'}, {u'op_instance': u'8', u'op_sequence': u'53', u'op': u'ncrcat'}, {u'op_instance': u'1', u'op_sequence': u'27', u'op': u'rm'}, {u'op_instance': u'10', u'op_sequence': u'54', u'op': u'rm'}, {u'op_instance': u'11', u'op_sequence': u'61', u'op': u'rm'}, {u'op_instance': u'13', u'op_sequence': u'63', u'op': u'rm'}, {u'op_instance': u'14', u'op_sequence': u'70', u'op': u'rm'}, {u'op_instance': u'16', u'op_sequence': u'75', u'op': u'rm'}, {u'op_instance': u'18', u'op_sequence': u'77', u'op': u'rm'}, {u'op_instance': u'19', u'op_sequence': u'88', u'op': u'rm'}, {u'op_instance': u'2', u'op_sequence': u'34', u'op': u'rm'}, {u'op_instance': u'4', u'op_sequence': u'36', u'op': u'rm'}, {u'op_instance': u'5', u'op_sequence': u'43', u'op': u'rm'}, {u'op_instance': u'7', u'op_sequence': u'45', u'op': u'rm'}, {u'op_instance': u'8', u'op_sequence': u'52', u'op': u'rm'}, {u'op_instance': u'2', u'op_sequence': u'81', u'op': u'splitvars'}, {u'op_instance': u'1', u'op_sequence': u'28', u'op': u'timavg'}, {u'op_instance': u'11', u'op_sequence': u'72', u'op': u'timavg'}, {u'op_instance': u'3', u'op_sequence': u'37', u'op': u'timavg'}, {u'op_instance': u'5', u'op_sequence': u'46', u'op': u'timavg'}, {u'op_instance': u'7', u'op_sequence': u'55', u'op': u'timavg'}, {u'op_instance': u'9', u'op_sequence': u'64', u'op': u'timavg'}, {u'op_instance': u'2', u'op_sequence': u'29', u'op': u'untar'}, {u'op_instance': u'3', u'op_sequence': u'38', u'op': u'untar'}, {u'op_instance': u'4', u'op_sequence': u'47', u'op': u'untar'}, {u'op_instance': u'5', u'op_sequence': u'56', u'op': u'untar'}, {u'op_instance': u'6', u'op_sequence': u'65', u'op': u'untar'}, {u'op_instance': u'7', u'op_sequence': u'78', u'op': u'untar'}], u'outblock': 23933624, u'delayacct_blkio_time': 0, u'num_procs': 3480, u'time_waiting': 10152666725, u'syscr': 2182175, u'rchar': 15458131996, u'syscw': 897834, u'processor': 0}, 'end': datetime(2019, 6, 15, 9, 39, 44, 317282), 'env_dict': {u'TMP': u'/vftmp/Jeffrey.Durachta/job685000', u'MODULE_VERSION': u'3.2.10', u'SLURM_NTASKS': u'1', u'ENVIRONMENT': u'BATCH', u'HOME': u'/home/Jeffrey.Durachta', u'SLURM_JOB_USER': u'Jeffrey.Durachta', u'LANG': u'en_US', u'SHELL': u'/bin/tcsh', u'SLURM_JOB_CPUS_PER_NODE': u'1', u'SLURM_JOB_QOS': u'Added as default', u'SLURM_GET_USER_ENV': u'1', u'SLURM_NODELIST': u'pp208', u'pp_script': u'/home/Jeffrey.Durachta/ESM4/DECK/ESM4_historical_D151/gfdl.ncrc4-intel16-prod-openmp/scripts/postProcess/ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101.tags', u'MANPATH': u'/home/gfdl/man:/usr/local/man:/usr/share/man', u'SLURM_PROCID': u'0', u'OSTYPE': u'linux', u'SLURM_TASKS_PER_NODE': u'1', u'VENDOR': u'unknown', u'JOB_ID': u'685000', u'jobname': u'ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101', u'SLURM_JOB_PARTITION': u'batch', u'HOST': u'pp208', u'SLURM_JOB_ID': u'685000', u'SLURM_NODE_ALIASES': u'(null)', u'SLURM_CPUS_ON_NODE': u'1', u'EPMT': u'/home/Jeffrey.Durachta/workflowDB/build//epmt/epmt', u'SLURM_PRIO_PROCESS': u'0', u'SLURM_GTIDS': u'0', u'SLURM_NODEID': u'0', u'SLURM_NNODES': u'1', u'MODULESHOME': u'/usr/local/Modules/3.2.10', u'SLURM_JOB_ACCOUNT': u'gfdl_f', u'MACHTYPE': u'x86_64', u'SLURMD_NODENAME': u'pp208', u'SLURM_LOCALID': u'0', u'GROUP': u'f', u'SLURM_SUBMIT_DIR': u'/home/Jeffrey.Durachta/ESM4/DECK/ESM4_historical_D151/gfdl.ncrc4-intel16-prod-openmp/scripts/postProcess', u'SLURM_JOBID': u'685000', u'HOSTTYPE': u'x86_64-linux', u'SLURM_TOPOLOGY_ADDR_PATTERN': u'node', u'LOGNAME': u'Jeffrey.Durachta', u'USER': u'Jeffrey.Durachta', u'PATH': u'/home/gfdl/bin2:/usr/local/bin:/bin:/usr/bin:.', u'SLURM_JOB_NAME': u'ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101', u'SLURM_JOB_NODELIST': u'pp208', u'SLURM_SUBMIT_HOST': u'an104', u'SLURM_CLUSTER_NAME': u'gfdl', u'SHLVL': u'2', u'SLURM_JOB_UID': u'4067', u'PAPIEX_OUTPUT': u'/vftmp/Jeffrey.Durachta/job685000/papiex/', u'SLURM_JOB_NUM_NODES': u'1', u'SLURM_WORKING_CLUSTER': u'gfdl:slurm01:6817:8448', u'ARCHIVE': u'/archive/Jeffrey.Durachta', u'SLURM_CHECKPOINT_IMAGE_DIR': u'/var/slurm/checkpoint', u'MODULE_VERSION_STACK': u'3.2.10', u'SLURM_NPROCS': u'1', u'TERM': u'dumb', u'SLURM_JOB_GID': u'70', u'TMPDIR': u'/vftmp/Jeffrey.Durachta/job685000', u'MODULEPATH': u'/usr/local/Modules/modulefiles:/home/fms/local/modulefiles', u'EPMT_JOB_TAGS': u'exp_name:ESM4_historical_D151;exp_component:ocean_annual_rho2_1x1deg;exp_time:18840101;atm_res:c96l49;ocn_res:0.5l75;script_name:ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101', u'OMP_NUM_THREADS': u'1', u'SLURM_TASK_PID': u'6089', u'SLURM_TOPOLOGY_ADDR': u'pp208', u'PWD': u'/vftmp/Jeffrey.Durachta/job685000', u'HOSTNAME': u'pp208', u'WORKFLOWDB_PATH': u'/home/Jeffrey.Durachta/workflowDB/build/', u'LOADEDMODULES': u'', u'LC_TIME': u'C'}, 'jobscriptname': u'', 'created_at': datetime(2019, 7, 8, 3, 29, 10, 475892), 'tags': {u'ocn_res': u'0.5l75', u'atm_res': u'c96l49', u'exp_component': u'ocean_annual_rho2_1x1deg', u'exp_name': u'ESM4_historical_D151', u'exp_time': u'18840101', u'script_name': u'ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101'}, 'account': None, 'updated_at': datetime(2019, 7, 8, 3, 29, 10, 475895), 'submit': datetime(2019, 6, 15, 7, 52, 4, 73965), 'jobid': u'685000', 'queue': None, 'start': datetime(2019, 6, 15, 7, 52, 4, 73965), 'sessionid': None, 'user': u'Jeffrey.Durachta', 'info_dict': {'tz': 'US/Eastern', 'status': {'exit_code': 0, 'exit_reason': 'none', 'script_name': 'ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101', 'script_path': '/home/Jeffrey.Durachta/ESM4/DECK/ESM4_historical_D151/gfdl.ncrc4-intel16-prod-openmp/scripts/postProcess/ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101.tags'}}, 'annotations': {}, 'analyses': {}, 'duration': 6460243317.0, 'cpu_time': 113135329.0, 'env_changes_dict': {}, 'jobname': u'ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101', 'exitcode': 0}

        self.assertEqual(job_dict['proc_sums']['all_proc_tags'], ref_dict['proc_sums']['all_proc_tags'], 'mismatch in all_proc_tags')
        self.assertEqual(job_dict['proc_sums'], ref_dict['proc_sums'], 'mismatch in proc_sums')

        # the keys below are only in the Pony model, and are slated for removal
        # so we skip checking for their presence
        # updated_at key is only present if the record has been updated
        ign_key_presence = ['jobscriptname', 'account', 'queue', 'sessionid', 'updated_at']

        self.assertEqual(set(job_dict.keys()) - set(ign_key_presence), set(ref_dict.keys()) - set(ign_key_presence))
        ign_key_values = set(ign_key_presence + ['created_at'])
        for (k,v) in ref_dict.items():
             if k in ign_key_values: continue
             self.assertEqual(job_dict[k], ref_dict[k], 'expected for key({0}): {1}; got {2}'.format(k, ref_dict[k], job_dict[k]))

    @db_session
    def test_proc_data(self):
        j = orm_get(Job, '685000')
        self.assertEqual(len(j.processes[:]) if settings.orm == 'sqlalchemy' else j.processes.count(), 3480, 'wrong proc count in job')
        self.assertEqual(sum([p.duration for p in j.processes]), 24717624686.0, 'wrong proc duration aggregate')

    @db_session
    def test_unprocessed_jobs(self):
        from orm import UnprocessedJob, orm_commit
        from epmt_job import post_process_pending_jobs, post_process_job
        with self.assertRaises(Exception):
             u = UnprocessedJob['685003']
        if settings.orm == 'sqlalchemy':
            # only sqlalchemy allows this option
            settings.post_process_job_on_ingest = False
        with capture() as (out,err):
            epmt_submit(glob('test/data/query/685003.tgz'), dry_run=False)
        settings.post_process_job_on_ingest = True
        j = Job['685003']
        if settings.orm == 'sqlalchemy':
            # proc_sums for job is calculated during post-process
            self.assertFalse(j.proc_sums)
            self.assertTrue(UnprocessedJob['685003'])
            self.assertEqual(eq.get_unprocessed_jobs(), [u'685003'])
            # now let's post-process all pending jobs
            u_jobs = post_process_pending_jobs()
            self.assertIn('685003', u_jobs)
        else:
            self.assertEqual(post_process_pending_jobs(), [])
        self.assertFalse(post_process_job(j))
        self.assertEqual(eq.get_unprocessed_jobs(), [])
        self.assertFalse(orm_get(UnprocessedJob, '685003'))
        with self.assertRaises(Exception):
             u = UnprocessedJob['685003']
        self.assertTrue(j.proc_sums)

    @db_session
    def test_corrupted_csv(self):
        datafiles='test/data/misc/corrupted-csv.tgz'
        # quell the error message
        set_logging(-2)
        with self.assertRaises(ValueError):
            epmt_submit(glob(datafiles), dry_run=False)
        # restore logging level
        set_logging(-1)
        

if __name__ == '__main__':
    unittest.main()
