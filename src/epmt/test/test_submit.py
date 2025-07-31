#!/usr/bin/env python

# the import below is crucial to get a sane test environment
import unittest
from datetime import datetime
from shutil import copyfile
from epmt.orm import Job, Process, UnprocessedJob, db_session, setup_db
from epmt.epmtlib import capture, epmt_logging_init, timing
import epmt.epmt_settings as settings

# import unittest
# from sys import stderr
# from glob import glob
# from os import environ
# from datetime import datetime
# import pandas as pd
#
# import epmt.epmt_settings as settings
# import epmt.epmt_query as eq
# from epmt.epmt_cmds import epmt_submit
#
# from epmt.epmtlib import timing, get_install_root, capture, epmt_logging_init
# from epmt.orm import db_session, setup_db, orm_db_provider

# from epmt.orm.sqlalchemy.general import orm_get
#
# this will be used repeatedly in the tests, so let's store it
# in a variable instead of repeatedly calling the function
# install_root = get_install_root()


# the import below is crucial to get a sane test environment


def do_cleanup():
    eq.delete_jobs(['685000', '685003', '685016', '2220', 'corrupted-csv',
                   '804268', '692500', '3455'], force=True, remove_models=True)


@timing
def setUpModule():
    datafiles = '{}/test/data/misc/685000.tgz'.format(install_root)
    settings.post_process_job_on_ingest = True
    settings.verbose = 2
    setup_db(settings)
#    print('\n' + str(settings.db_params))
#    print('setUpModule: importing {0}'.format(datafiles))
    do_cleanup()
    with capture() as (out, err):
        epmt_submit(glob(datafiles), dry_run=False, remove_on_success=False, move_on_failure=False)


def tearDownModule():
    do_cleanup()


class EPMTSubmit(unittest.TestCase):
    @db_session
    def test_all_job_data(self):
        job_dict = eq.orm_to_dict(Job['685000'])

        # we remove the field below as it cannot be compared with a reference
        # (it contains database row IDs, which will change from run to run
        # del job_dict['annotations']['papiex-error-process-ids']
        ref_dict = {'proc_sums': {'majflt': 8,
                                  'systemtime': 41980075,
                                  'invol_ctxsw': 20900,
                                  'inblock': 13672,
                                  'vol_ctxsw': 770843,
                                  'read_bytes': 7000064,
                                  'PERF_COUNT_SW_CPU_CLOCK': 86903088007,
                                  'cancelled_write_bytes': 8925798400,
                                  'timeslices': 795433,
                                  'wchar': 15066048420,
                                  'guest_time': 0,
                                  'rssmax': 31621528,
                                  'num_threads': 3668,
                                  'write_bytes': 12254015488,
                                  'minflt': 4972187,
                                  'rdtsc_duration': -1,
                                  'usertime': 71155254,
                                  'time_oncpu': 115330986461,
                                  'all_proc_tags': [{'op_instance': '11',
                                                     'op_sequence': '66',
                                                     'op': 'cp'},
                                                    {'op_instance': '15',
                                                     'op_sequence': '79',
                                                     'op': 'cp'},
                                                    {'op_instance': '3',
                                                     'op_sequence': '30',
                                                     'op': 'cp'},
                                                    {'op_instance': '5',
                                                     'op_sequence': '39',
                                                     'op': 'cp'},
                                                    {'op_instance': '7',
                                                     'op_sequence': '48',
                                                     'op': 'cp'},
                                                    {'op_instance': '9',
                                                     'op_sequence': '57',
                                                     'op': 'cp'},
                                                    {'op_instance': '2',
                                                     'op_sequence': '89',
                                                     'op': 'dmput'},
                                                    {'op_instance': '2',
                                                     'op_sequence': '31',
                                                     'op': 'fregrid'},
                                                    {'op_instance': '3',
                                                     'op_sequence': '40',
                                                     'op': 'fregrid'},
                                                    {'op_instance': '4',
                                                     'op_sequence': '49',
                                                     'op': 'fregrid'},
                                                    {'op_instance': '5',
                                                     'op_sequence': '58',
                                                     'op': 'fregrid'},
                                                    {'op_instance': '6',
                                                     'op_sequence': '67',
                                                     'op': 'fregrid'},
                                                    {'op_instance': '7',
                                                     'op_sequence': '80',
                                                     'op': 'fregrid'},
                                                    {'op_instance': '1',
                                                     'op_sequence': '1',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '1',
                                                     'op_sequence': '3',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '1',
                                                     'op_sequence': '5',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '1',
                                                     'op_sequence': '7',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '1',
                                                     'op_sequence': '9',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '3',
                                                     'op_sequence': '10',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '3',
                                                     'op_sequence': '2',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '3',
                                                     'op_sequence': '4',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '3',
                                                     'op_sequence': '6',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '3',
                                                     'op_sequence': '8',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '4',
                                                     'op_sequence': '11',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '4',
                                                     'op_sequence': '14',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '4',
                                                     'op_sequence': '17',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '4',
                                                     'op_sequence': '20',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '4',
                                                     'op_sequence': '23',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '6',
                                                     'op_sequence': '12',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '6',
                                                     'op_sequence': '15',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '6',
                                                     'op_sequence': '18',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '6',
                                                     'op_sequence': '21',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '6',
                                                     'op_sequence': '24',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '7',
                                                     'op_sequence': '13',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '7',
                                                     'op_sequence': '16',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '7',
                                                     'op_sequence': '19',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '7',
                                                     'op_sequence': '22',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '7',
                                                     'op_sequence': '25',
                                                     'op': 'hsmget'},
                                                    {'op_instance': '1',
                                                     'op_sequence': '33',
                                                     'op': 'mv'},
                                                    {'op_instance': '10',
                                                     'op_sequence': '60',
                                                     'op': 'mv'},
                                                    {'op_instance': '13',
                                                     'op_sequence': '69',
                                                     'op': 'mv'},
                                                    {'op_instance': '16',
                                                     'op_sequence': '74',
                                                     'op': 'mv'},
                                                    {'op_instance': '18',
                                                     'op_sequence': '83',
                                                     'op': 'mv'},
                                                    {'op_instance': '18',
                                                     'op_sequence': '86',
                                                     'op': 'mv'},
                                                    {'op_instance': '20',
                                                     'op_sequence': '84',
                                                     'op': 'mv'},
                                                    {'op_instance': '20',
                                                     'op_sequence': '87',
                                                     'op': 'mv'},
                                                    {'op_instance': '4',
                                                     'op_sequence': '42',
                                                     'op': 'mv'},
                                                    {'op_instance': '7',
                                                     'op_sequence': '51',
                                                     'op': 'mv'},
                                                    {'op_instance': '11',
                                                     'op_sequence': '68',
                                                     'op': 'ncatted'},
                                                    {'op_instance': '12',
                                                     'op_sequence': '73',
                                                     'op': 'ncatted'},
                                                    {'op_instance': '15',
                                                     'op_sequence': '82',
                                                     'op': 'ncatted'},
                                                    {'op_instance': '15',
                                                     'op_sequence': '85',
                                                     'op': 'ncatted'},
                                                    {'op_instance': '3',
                                                     'op_sequence': '32',
                                                     'op': 'ncatted'},
                                                    {'op_instance': '5',
                                                     'op_sequence': '41',
                                                     'op': 'ncatted'},
                                                    {'op_instance': '7',
                                                     'op_sequence': '50',
                                                     'op': 'ncatted'},
                                                    {'op_instance': '9',
                                                     'op_sequence': '59',
                                                     'op': 'ncatted'},
                                                    {'op_instance': '10',
                                                     'op_sequence': '62',
                                                     'op': 'ncrcat'},
                                                    {'op_instance': '12',
                                                     'op_sequence': '71',
                                                     'op': 'ncrcat'},
                                                    {'op_instance': '13',
                                                     'op_sequence': '76',
                                                     'op': 'ncrcat'},
                                                    {'op_instance': '2',
                                                     'op_sequence': '26',
                                                     'op': 'ncrcat'},
                                                    {'op_instance': '4',
                                                     'op_sequence': '35',
                                                     'op': 'ncrcat'},
                                                    {'op_instance': '6',
                                                     'op_sequence': '44',
                                                     'op': 'ncrcat'},
                                                    {'op_instance': '8',
                                                     'op_sequence': '53',
                                                     'op': 'ncrcat'},
                                                    {'op_instance': '1',
                                                     'op_sequence': '27',
                                                     'op': 'rm'},
                                                    {'op_instance': '10',
                                                     'op_sequence': '54',
                                                     'op': 'rm'},
                                                    {'op_instance': '11',
                                                     'op_sequence': '61',
                                                     'op': 'rm'},
                                                    {'op_instance': '13',
                                                     'op_sequence': '63',
                                                     'op': 'rm'},
                                                    {'op_instance': '14',
                                                     'op_sequence': '70',
                                                     'op': 'rm'},
                                                    {'op_instance': '16',
                                                     'op_sequence': '75',
                                                     'op': 'rm'},
                                                    {'op_instance': '18',
                                                     'op_sequence': '77',
                                                     'op': 'rm'},
                                                    {'op_instance': '19',
                                                     'op_sequence': '88',
                                                     'op': 'rm'},
                                                    {'op_instance': '2',
                                                     'op_sequence': '34',
                                                     'op': 'rm'},
                                                    {'op_instance': '4',
                                                     'op_sequence': '36',
                                                     'op': 'rm'},
                                                    {'op_instance': '5',
                                                     'op_sequence': '43',
                                                     'op': 'rm'},
                                                    {'op_instance': '7',
                                                     'op_sequence': '45',
                                                     'op': 'rm'},
                                                    {'op_instance': '8',
                                                     'op_sequence': '52',
                                                     'op': 'rm'},
                                                    {'op_instance': '2',
                                                     'op_sequence': '81',
                                                     'op': 'splitvars'},
                                                    {'op_instance': '1',
                                                     'op_sequence': '28',
                                                     'op': 'timavg'},
                                                    {'op_instance': '11',
                                                     'op_sequence': '72',
                                                     'op': 'timavg'},
                                                    {'op_instance': '3',
                                                     'op_sequence': '37',
                                                     'op': 'timavg'},
                                                    {'op_instance': '5',
                                                     'op_sequence': '46',
                                                     'op': 'timavg'},
                                                    {'op_instance': '7',
                                                     'op_sequence': '55',
                                                     'op': 'timavg'},
                                                    {'op_instance': '9',
                                                     'op_sequence': '64',
                                                     'op': 'timavg'},
                                                    {'op_instance': '2',
                                                     'op_sequence': '29',
                                                     'op': 'untar'},
                                                    {'op_instance': '3',
                                                     'op_sequence': '38',
                                                     'op': 'untar'},
                                                    {'op_instance': '4',
                                                     'op_sequence': '47',
                                                     'op': 'untar'},
                                                    {'op_instance': '5',
                                                     'op_sequence': '56',
                                                     'op': 'untar'},
                                                    {'op_instance': '6',
                                                     'op_sequence': '65',
                                                     'op': 'untar'},
                                                    {'op_instance': '7',
                                                     'op_sequence': '78',
                                                     'op': 'untar'}],
                                  'outblock': 23933624,
                                  'delayacct_blkio_time': 0,
                                  'num_procs': 3480,
                                  'time_waiting': 10152666725,
                                  'syscr': 2182175,
                                  'rchar': 15458131996,
                                  'syscw': 897834,
                                  'processor': 0},
                    'end': datetime(2019,
                                    6,
                                    15,
                                    9,
                                    39,
                                    44,
                                    317282),
                    'env_dict': {'TMP': '/vftmp/Jeffrey.Durachta/job685000',
                                 'MODULE_VERSION': '3.2.10',
                                 'SLURM_NTASKS': '1',
                                 'ENVIRONMENT': 'BATCH',
                                 'HOME': '/home/Jeffrey.Durachta',
                                 'SLURM_JOB_USER': 'Jeffrey.Durachta',
                                 'LANG': 'en_US',
                                 'SHELL': '/bin/tcsh',
                                 'SLURM_JOB_CPUS_PER_NODE': '1',
                                 'SLURM_JOB_QOS': 'Added as default',
                                 'SLURM_GET_USER_ENV': '1',
                                 'SLURM_NODELIST': 'pp208',
                                 'pp_script': '/home/Jeffrey.Durachta/ESM4/DECK/ESM4_historical_D151/gfdl.ncrc4-intel16-prod-openmp/scripts/postProcess/ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101.tags',
                                 'MANPATH': '/home/gfdl/man:/usr/local/man:/usr/share/man',
                                 'SLURM_PROCID': '0',
                                 'OSTYPE': 'linux',
                                 'SLURM_TASKS_PER_NODE': '1',
                                 'VENDOR': 'unknown',
                                 'JOB_ID': '685000',
                                 'jobname': 'ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101',
                                 'SLURM_JOB_PARTITION': 'batch',
                                 'HOST': 'pp208',
                                 'SLURM_JOB_ID': '685000',
                                 'SLURM_NODE_ALIASES': '(null)',
                                 'SLURM_CPUS_ON_NODE': '1',
                                 'EPMT': '/home/Jeffrey.Durachta/workflowDB/build//epmt/epmt',
                                 'SLURM_PRIO_PROCESS': '0',
                                 'SLURM_GTIDS': '0',
                                 'SLURM_NODEID': '0',
                                 'SLURM_NNODES': '1',
                                 'MODULESHOME': '/usr/local/Modules/3.2.10',
                                 'SLURM_JOB_ACCOUNT': 'gfdl_f',
                                 'MACHTYPE': 'x86_64',
                                 'SLURMD_NODENAME': 'pp208',
                                 'SLURM_LOCALID': '0',
                                 'GROUP': 'f',
                                 'SLURM_SUBMIT_DIR': '/home/Jeffrey.Durachta/ESM4/DECK/ESM4_historical_D151/gfdl.ncrc4-intel16-prod-openmp/scripts/postProcess',
                                 'SLURM_JOBID': '685000',
                                 'HOSTTYPE': 'x86_64-linux',
                                 'SLURM_TOPOLOGY_ADDR_PATTERN': 'node',
                                 'LOGNAME': 'Jeffrey.Durachta',
                                 'USER': 'Jeffrey.Durachta',
                                 'PATH': '/home/gfdl/bin2:/usr/local/bin:/bin:/usr/bin:.',
                                 'SLURM_JOB_NAME': 'ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101',
                                 'SLURM_JOB_NODELIST': 'pp208',
                                 'SLURM_SUBMIT_HOST': 'an104',
                                 'SLURM_CLUSTER_NAME': 'gfdl',
                                 'SHLVL': '2',
                                 'SLURM_JOB_UID': '4067',
                                 'PAPIEX_OUTPUT': '/vftmp/Jeffrey.Durachta/job685000/papiex/',
                                 'SLURM_JOB_NUM_NODES': '1',
                                 'SLURM_WORKING_CLUSTER': 'gfdl:slurm01:6817:8448',
                                 'ARCHIVE': '/archive/Jeffrey.Durachta',
                                 'SLURM_CHECKPOINT_IMAGE_DIR': '/var/slurm/checkpoint',
                                 'MODULE_VERSION_STACK': '3.2.10',
                                 'SLURM_NPROCS': '1',
                                 'TERM': 'dumb',
                                 'SLURM_JOB_GID': '70',
                                 'TMPDIR': '/vftmp/Jeffrey.Durachta/job685000',
                                 'MODULEPATH': '/usr/local/Modules/modulefiles:/home/fms/local/modulefiles',
                                 'EPMT_JOB_TAGS': 'exp_name:ESM4_historical_D151;exp_component:ocean_annual_rho2_1x1deg;exp_time:18840101;atm_res:c96l49;ocn_res:0.5l75;script_name:ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101',
                                 'OMP_NUM_THREADS': '1',
                                 'SLURM_TASK_PID': '6089',
                                 'SLURM_TOPOLOGY_ADDR': 'pp208',
                                 'PWD': '/vftmp/Jeffrey.Durachta/job685000',
                                 'HOSTNAME': 'pp208',
                                 'WORKFLOWDB_PATH': '/home/Jeffrey.Durachta/workflowDB/build/',
                                 'LOADEDMODULES': '',
                                 'LC_TIME': 'C'},
                    'jobscriptname': '',
                    'created_at': datetime(2019,
                                           7,
                                           8,
                                           3,
                                           29,
                                           10,
                                           475892),
                    'tags': {'ocn_res': '0.5l75',
                             'atm_res': 'c96l49',
                             'exp_component': 'ocean_annual_rho2_1x1deg',
                             'exp_name': 'ESM4_historical_D151',
                             'exp_time': '18840101',
                             'script_name': 'ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101'},
                    'account': None,
                    'updated_at': datetime(2019,
                                           7,
                                           8,
                                           3,
                                           29,
                                           10,
                                           475895),
                    'submit': datetime(2019,
                                       6,
                                       15,
                                       7,
                                       52,
                                       4,
                                       73965),
                    'jobid': '685000',
                    'queue': None,
                    'start': datetime(2019,
                                      6,
                                      15,
                                      7,
                                      52,
                                      4,
                                      73965),
                    'sessionid': None,
                    'user': 'Jeffrey.Durachta',
                    'info_dict': {'post_processed': 1,
                                  'procs_in_process_table': 1,
                                  'tz': 'US/Eastern',
                                  'status': {'exit_code': 0,
                                             'exit_reason': 'none',
                                             'script_name': 'ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101',
                                             'script_path': '/home/Jeffrey.Durachta/ESM4/DECK/ESM4_historical_D151/gfdl.ncrc4-intel16-prod-openmp/scripts/postProcess/ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101.tags'},
                                  'metric_names': 'PERF_COUNT_SW_CPU_CLOCK,cancelled_write_bytes,delayacct_blkio_time,guest_time,inblock,invol_ctxsw,majflt,minflt,outblock,processor,rchar,rdtsc_duration,read_bytes,rssmax,syscr,syscw,systemtime,time_oncpu,time_waiting,timeslices,usertime,vol_ctxsw,wchar,write_bytes'},
                    'annotations': {'papiex-error': 'PAPI failed or misbehaved process closed a descriptor it did not own (rdtsc_duration < 0). 4 processes have potentially erroneous PAPI metric counts',
                                    'EPMT_JOB_TAGS': 'atm_res:c96l49;exp_component:ocean_annual_rho2_1x1deg;exp_name:ESM4_historical_D151;exp_time:18840101;ocn_res:0.5l75;script_name:ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101',
                                    'papiex-error-process-ids': [22121,
                                                                 23756,
                                                                 24562,
                                                                 26138]},
                    'analyses': {},
                    'duration': 6460243317.0,
                    'cpu_time': 113135329.0,
                    'env_changes_dict': {},
                    'jobname': 'ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101',
                    'exitcode': 0}

        self.assertEqual(
            job_dict['proc_sums']['all_proc_tags'],
            ref_dict['proc_sums']['all_proc_tags'],
            'mismatch in all_proc_tags')
        self.assertEqual(job_dict['proc_sums'], ref_dict['proc_sums'], 'mismatch in proc_sums')

        # the keys below are only in the Pony model, and are slated for removal
        # so we skip checking for their presence
        # updated_at key is only present if the record has been updated
        ign_key_presence = ['jobscriptname', 'account', 'queue', 'sessionid', 'updated_at']

        self.assertEqual(set(job_dict.keys()) - set(ign_key_presence), set(ref_dict.keys()) - set(ign_key_presence))
        ign_key_values = set(ign_key_presence + ['created_at'])
        for (k, v) in ref_dict.items():
            if k in ign_key_values:
                continue
            self.assertEqual(
                job_dict[k],
                ref_dict[k],
                'expected for key({0}): {1}; got {2}'.format(
                    k,
                    ref_dict[k],
                    job_dict[k]))

    @db_session
    def test_all_proc_data(self):
        j = orm_get(Job, '685000')
        self.assertEqual(len(j.processes[:]) if settings.orm ==
                         'sqlalchemy' else j.processes.count(), 3480, 'wrong proc count in job')
        self.assertEqual(sum([p.duration for p in j.processes]), 24717624686.0, 'wrong proc duration aggregate')

    @db_session
    def test_dry_run(self):
        with self.assertRaises(Exception):
            Job['685003']
        with capture() as (out, err):
            epmt_submit(['{}/test/data/query/685003.tgz'.format(get_install_root())],
                        dry_run=True, remove_on_success=False, move_on_failure=False)
        # the job should still not be in the database
        with self.assertRaises(Exception):
            Job['685003']

    @db_session
    def test_submit_dir(self):
        with self.assertRaises(Exception):
            Job['3455']
        with capture() as (out, err):
            epmt_submit(['{}/test/data/submit/3455/'.format(get_install_root())],
                        dry_run=False, remove_on_success=False, move_on_failure=False)
        j = Job['3455']
        self.assertEqual(j.duration, 28111.0)

    @db_session
    def test_submit_minus_e(self):
        with self.assertRaises(Exception):
            Job['685003']
        Job['685000']
        # quell the error message
        epmt_logging_init(-2)
        with capture() as (out, err):
            epmt_submit(['{}/test/data/query/685000.tgz'.format(install_root),
                         '{}/test/data/query/685003.tgz'.format(install_root)],
                        keep_going=False,
                        dry_run=False,
                        remove_on_success=False,
                        move_on_failure=False)
        # restore logging level
        epmt_logging_init(-1)
        # because keep_going is disabled, when we find 685000 in the db,
        # we should not attempt to ingest 685003
        with self.assertRaises(Exception):
            Job['685003']

    @db_session
    def test_unprocessed_jobs(self):
        from epmt.orm import UnprocessedJob, orm_commit
        from epmt.epmt_job import post_process_pending_jobs, post_process_job
        with self.assertRaises(Exception):
            u = UnprocessedJob['685003']
        if settings.orm == 'sqlalchemy':
            # only sqlalchemy allows this option
            settings.post_process_job_on_ingest = False
        with capture() as (out, err):
            epmt_submit(glob('{}/test/data/query/685003.tgz'.format(install_root)),
                        dry_run=False, remove_on_success=False, move_on_failure=False)
        settings.post_process_job_on_ingest = True
        j = Job['685003']
        if settings.orm == 'sqlalchemy':
            # proc_sums for job is calculated during post-process
            self.assertFalse(j.proc_sums)
            self.assertTrue(UnprocessedJob['685003'])
            self.assertIn('685003', eq.get_unprocessed_jobs())
            # now we call get_jobs with a flag to prevent triggering PP
            jobs_dict = eq.get_jobs('685003', fmt='dict', trigger_post_process=False)[0]
            self.assertFalse(jobs_dict['proc_sums'])
            self.assertFalse(jobs_dict.get('time_waiting', None))
            # now trigger PP for 685003
            jobs_dict = eq.get_jobs('685003', fmt='dict')[0]
            self.assertTrue(jobs_dict['time_waiting'])
        else:
            self.assertEqual(post_process_pending_jobs(), [])
        self.assertFalse('685003' in eq.get_unprocessed_jobs())
        self.assertFalse(post_process_job(j.jobid))
        self.assertFalse(orm_get(UnprocessedJob, '685003'))
        with self.assertRaises(Exception):
            u = UnprocessedJob['685003']
        self.assertTrue(eq.is_job_post_processed(j))

    @db_session
    def test_unprocessed_jobs_auto_post_process(self):
        from epmt.orm import UnprocessedJob
        saved_val = settings.post_process_job_on_ingest
        if settings.orm == 'sqlalchemy':
            # only sqla supports this setting
            settings.post_process_job_on_ingest = False
        with capture() as (out, err):
            epmt_submit(['{}/test/data/query/685016.tgz'.format(install_root)],
                        dry_run=False, remove_on_success=False, move_on_failure=False)
        # restore the old setting
        settings.post_process_job_on_ingest = saved_val
        # make sure we can do a conv_jobs on the job without
        # raising an exception
        df = eq.conv_jobs('685016', fmt='pandas')
        # we are guaranteed that the job will be post-processed
        # as conv_jobs will post-process unprocessed jobs
        self.assertTrue(list(df.rssmax.values))
        self.assertTrue(eq.is_job_post_processed('685016'))

    @db_session
    def test_convert_csv(self):
        import tempfile
        from epmt.epmt_convert_csv import convert_csv_in_tar
        job_dict_csv = eq.get_jobs('685000', fmt='dict', limit=1, trigger_post_process=True)[0]
        eq.delete_jobs('685000')

        (_, new_tar) = tempfile.mkstemp(prefix='epmt_', suffix='_collated_tsv.tgz')
#        self.assertTrue(convert_csv_in_tar('{}/test/data/query/685000.tgz'.format(install_root), new_tar))
        self.assertTrue(convert_csv_in_tar('{}/test/data/misc/685000.tgz'.format(install_root), new_tar))
        with capture() as (out, err):
            epmt_submit(glob(new_tar), dry_run=False, remove_on_success=True, move_on_failure=False)

        job_dict_tsv = eq.get_jobs('685000', fmt='dict', limit=1)[0]
        self.assertEqual(set(job_dict_csv), set(job_dict_tsv))

        # we remove the field below from both dicts as it consists
        # of database ids, which will change from run to run
        # del job_dict_csv['annotations']['papiex-error-process-ids']
        # del job_dict_tsv['annotations']['papiex-error-process-ids']
        # now compare the values for each key, skipping over timestamps
        for k in job_dict_csv.keys():
            if k in {'updated_at', 'created_at'}:
                continue
            self.assertEqual(job_dict_csv[k], job_dict_tsv[k], "Dicts differ for key: {}".format(k))

    @db_session
    def test_collated_tsv(self):
        datafile = '{}/test/data/tsv/collated-tsv-2220.tgz'.format(install_root)
        with capture() as (out, err):
            epmt_submit([datafile], dry_run=False, remove_on_success=False, move_on_failure=False)
        j = Job['2220']
        if orm_db_provider() == 'postgres' and settings.orm == 'sqlalchemy':
            # in postgres+SQLA the processes are put in a staging table
            self.assertTrue(eq.is_job_in_staging(j))
            self.assertFalse(eq.is_job_post_processed(j))
            self.assertFalse(j.processes)
            # the orm_to_dict will trigger moving the job from staging
            # to processes table and post-processing it in case it's
            # not post_processes
            j_dict = orm_to_dict(j)
        # at this point the processes will be in the process table
        # and would have been post-processed
        self.assertFalse(eq.is_job_in_staging(j))
        self.assertTrue(eq.is_job_post_processed(j))
        # confirm that the processing went right
        self.assertEqual(len(j.processes), 2)
        self.assertEqual(j.proc_sums['rssmax'], 9952)

    @db_session
    def test_corrupted_csv(self):
        datafile = '{}/test/data/misc/corrupted-csv.tgz'.format(install_root)
        # quell the error message
        epmt_logging_init(-2)
        with self.assertRaises(ValueError):
            epmt_submit([datafile], dry_run=False, remove_on_success=True, move_on_failure=False)
        # restore logging level
        epmt_logging_init(-1)
        from os import path
        # make sure submit did not remove the input .tgz
        # (for failed submission input is never removed, even if
        self.assertTrue(path.isfile(datafile))

    def check_lazy_compute(self, j, lazy_eval):
        from epmt.epmt_job import is_process_tree_computed, mk_process_tree
        from epmt.orm import Process
        p = eq.get_procs(j, limit=1, order=Process.start, fmt='orm')[0]
        is_pt_computed = is_process_tree_computed(j)
        if lazy_eval:
            self.assertFalse(is_pt_computed)
            self.assertIsNone(p.parent)
            self.assertFalse(p.children)
            self.assertIsNone(p.inclusive_cpu_time)
            mk_process_tree(j)
            self.assertTrue(p.inclusive_cpu_time)
            self.assertTrue(p.parent or p.children)
            self.assertTrue(is_process_tree_computed(j))
        else:
            self.assertTrue(is_pt_computed)
            self.assertTrue(p.inclusive_cpu_time)
            self.assertTrue(is_process_tree_computed(j))

    @db_session
    def test_lazy_compute_process_tree(self):
        orig_lazy_eval = settings.lazy_compute_process_tree
        self.check_lazy_compute(Job['685000'], orig_lazy_eval)
        datafiles = '{}/test/data/submit/804268.tgz'.format(install_root)
        settings.lazy_compute_process_tree = not (orig_lazy_eval)  # toggle setting
        with capture() as (out, err):
            epmt_submit(glob(datafiles), dry_run=False, remove_on_success=False, move_on_failure=False)
        self.check_lazy_compute(Job['804268'], settings.lazy_compute_process_tree)
        settings.lazy_compute_process_tree = orig_lazy_eval  # restore old setting

    def test_submit_remove(self):
        from shutil import copyfile
        from os import path
        target = '/tmp/692500.tgz'
        copyfile('{}/test/data/submit/692500.tgz'.format(install_root), target)
        self.assertTrue(path.isfile(target))
        self.assertFalse('692500' in eq.get_jobs(fmt='terse'))
        with capture() as (out, err):
            epmt_submit([target], dry_run=False, remove_on_success=True, move_on_failure=False)
        self.assertTrue('692500' in eq.get_jobs(fmt='terse'))
        self.assertFalse(path.isfile(target))


if __name__ == '__main__':
    unittest.main()
