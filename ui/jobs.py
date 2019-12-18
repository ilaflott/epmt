# Generate a random list of jobs
from string import ascii_letters
import random
import datetime
import time
import pandas as pd

# Index.py Configures logger debug level
from logging import getLogger, basicConfig, DEBUG, ERROR, INFO, WARNING
logger = getLogger(__name__)  # you can use other name

samplej = {'duration': 6460243317.0,
           'updated_at': datetime.datetime(2019, 11, 26, 22, 0, 22, 485979),
           'tags': {'exp_name': 'ESM4_historical_D151',
                    'exp_component': 'ocean_annual_rho2_1x1deg',
                    'exp_time': '18840101',
                    'atm_res': 'c96l49',
                    'ocn_res': '0.5l75',
                    'script_name': 'ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101'},
           'info_dict': {'tz': 'US/Eastern',
                         'status': {'exit_code': 0,
                                    'exit_reason': 'none',
                                    'script_path': '/home/Jeffrey.Durachta/ESM4/DECK/ESM4_historical_D151/gfdl.ncrc4-intel16-prod-openmp/scripts/postProcess/ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101.tags',
                                    'script_name': 'ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101'}},
           'env_dict': {'TMP': '/vftmp/Jeffrey.Durachta/job685000',
                        'MODULE_VERSION': '3.2.10',
                        'GROUP': 'f',
                        'SLURM_SUBMIT_DIR': '/home/Jeffrey.Durachta/ESM4/DECK/ESM4_historical_D151/gfdl.ncrc4-intel16-prod-openmp/scripts/postProcess',
                        'SLURM_NODEID': '0',
                        'SLURM_JOBID': '685000',
                        'HOSTTYPE': 'x86_64-linux',
                        'ENVIRONMENT': 'BATCH',
                        'MODULESHOME': '/usr/local/Modules/3.2.10',
                        'SLURM_LOCALID': '0',
                        'LOGNAME': 'Jeffrey.Durachta',
                        'USER': 'Jeffrey.Durachta',
                        'HOME': '/home/Jeffrey.Durachta',
                        'PATH': '/home/gfdl/bin2:/usr/local/bin:/bin:/usr/bin:.',
                        'SLURM_JOB_NODELIST': 'pp208',
                        'SLURM_JOB_USER': 'Jeffrey.Durachta',
                        'LANG': 'en_US',
                        'TERM': 'dumb',
                        'SHELL': '/bin/tcsh',
                        'SLURM_JOB_CPUS_PER_NODE': '1',
                        'SHLVL': '2',
                        'SLURM_JOB_QOS': 'Added as default',
                        'SLURM_JOB_UID': '4067',
                        'SLURM_GET_USER_ENV': '1',
                        'SLURM_NODELIST': 'pp208',
                        'pp_script': '/home/Jeffrey.Durachta/ESM4/DECK/ESM4_historical_D151/gfdl.ncrc4-intel16-prod-openmp/scripts/postProcess/ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101.tags',
                        'PAPIEX_OUTPUT': '/vftmp/Jeffrey.Durachta/job685000/papiex/',
                        'SLURM_JOB_NUM_NODES': '1',
                        'MANPATH': '/home/gfdl/man:/usr/local/man:/usr/share/man',
                        'SLURM_PROCID': '0',
                        'OSTYPE': 'linux',
                        'SLURM_TASKS_PER_NODE': '1',
                        'HOSTNAME': 'pp208',
                        'ARCHIVE': '/archive/Jeffrey.Durachta',
                        'SLURM_SUBMIT_HOST': 'an104',
                        'VENDOR': 'unknown',
                        'JOB_ID': '685000',
                        'MODULE_VERSION_STACK': '3.2.10',
                        'SLURM_CLUSTER_NAME': 'gfdl',
                        'jobname': 'ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101',
                        'SLURM_JOB_PARTITION': 'batch',
                        'HOST': 'pp208',
                        'SLURM_JOB_ID': '685000',
                        'SLURM_NTASKS': '1',
                        'SLURM_NODE_ALIASES': '(null)',
                        'SLURM_CPUS_ON_NODE': '1',
                        'LOADEDMODULES': '',
                        'SLURM_JOB_GID': '70',
                        'TMPDIR': '/vftmp/Jeffrey.Durachta/job685000',
                        'MODULEPATH': '/usr/local/Modules/modulefiles:/home/fms/local/modulefiles',
                        'EPMT': '/home/Jeffrey.Durachta/workflowDB/build//epmt/epmt',
                        'SLURM_NPROCS': '1',
                        'EPMT_JOB_TAGS': 'exp_name:ESM4_historical_D151;exp_component:ocean_annual_rho2_1x1deg;exp_time:18840101;atm_res:c96l49;ocn_res:0.5l75;script_name:ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101',
                        'SLURM_PRIO_PROCESS': '0',
                        'OMP_NUM_THREADS': '1',
                        'SLURM_CHECKPOINT_IMAGE_DIR': '/var/slurm/checkpoint',
                        'SLURM_GTIDS': '0',
                        'SLURM_TASK_PID': '6089',
                        'SLURM_NNODES': '1',
                        'SLURM_JOB_NAME': 'ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101',
                        'SLURM_TOPOLOGY_ADDR': 'pp208',
                        'PWD': '/vftmp/Jeffrey.Durachta/job685000',
                        'SLURM_TOPOLOGY_ADDR_PATTERN': 'node',
                        'WORKFLOWDB_PATH': '/home/Jeffrey.Durachta/workflowDB/build/',
                        'SLURM_JOB_ACCOUNT': 'gfdl_f',
                        'LC_TIME': 'C',
                        'MACHTYPE': 'x86_64',
                        'SLURMD_NODENAME': 'pp208',
                        'SLURM_WORKING_CLUSTER': 'gfdl:slurm01:6817:8448'},
           'cpu_time': 113135329.0,
           'annotations': {},
           'env_changes_dict': {},
           'analyses': {},
           'submit': datetime.datetime(2019, 6, 15, 7, 52, 4, 73965),
           'start': datetime.datetime(2019, 6, 15, 7, 52, 4, 73965),
           'jobid': 'job1',
           'end': datetime.datetime(2019, 6, 15, 9, 39, 44, 317282),
           'jobname': 'ESM4_historical_D151_ocean_annual_rho2_1x1deg_18840101',
           'created_at': datetime.datetime(2019, 11, 26, 22, 0, 8, 937521),
           'exitcode': 0,
           'user': 'Jeffrey.Durachta',
           'all_proc_tags': [{'op': 'cp', 'op_instance': '11', 'op_sequence': '66'},
                             {'op': 'cp', 'op_instance': '15', 'op_sequence': '79'},
                             {'op': 'cp', 'op_instance': '3', 'op_sequence': '30'},
                             {'op': 'cp', 'op_instance': '5', 'op_sequence': '39'},
                             {'op': 'cp', 'op_instance': '7', 'op_sequence': '48'},
                             {'op': 'cp', 'op_instance': '9', 'op_sequence': '57'},
                             {'op': 'dmput', 'op_instance': '2',
                                 'op_sequence': '89'},
                             {'op': 'fregrid', 'op_instance': '2',
                                 'op_sequence': '31'},
                             {'op': 'fregrid', 'op_instance': '3',
                                 'op_sequence': '40'},
                             {'op': 'fregrid', 'op_instance': '4',
                                 'op_sequence': '49'},
                             {'op': 'fregrid', 'op_instance': '5',
                                 'op_sequence': '58'},
                             {'op': 'fregrid', 'op_instance': '6',
                                 'op_sequence': '67'},
                             {'op': 'fregrid', 'op_instance': '7',
                                 'op_sequence': '80'},
                             {'op': 'hsmget', 'op_instance': '1', 'op_sequence': '1'},
                             {'op': 'hsmget', 'op_instance': '1', 'op_sequence': '3'},
                             {'op': 'hsmget', 'op_instance': '1', 'op_sequence': '5'},
                             {'op': 'hsmget', 'op_instance': '1', 'op_sequence': '7'},
                             {'op': 'hsmget', 'op_instance': '1', 'op_sequence': '9'},
                             {'op': 'hsmget', 'op_instance': '3',
                                 'op_sequence': '10'},
                             {'op': 'hsmget', 'op_instance': '3', 'op_sequence': '2'},
                             {'op': 'hsmget', 'op_instance': '3', 'op_sequence': '4'},
                             {'op': 'hsmget', 'op_instance': '3', 'op_sequence': '6'},
                             {'op': 'hsmget', 'op_instance': '3', 'op_sequence': '8'},
                             {'op': 'hsmget', 'op_instance': '4',
                                 'op_sequence': '11'},
                             {'op': 'hsmget', 'op_instance': '4',
                                 'op_sequence': '14'},
                             {'op': 'hsmget', 'op_instance': '4',
                                 'op_sequence': '17'},
                             {'op': 'hsmget', 'op_instance': '4',
                                 'op_sequence': '20'},
                             {'op': 'hsmget', 'op_instance': '4',
                                 'op_sequence': '23'},
                             {'op': 'hsmget', 'op_instance': '6',
                                 'op_sequence': '12'},
                             {'op': 'hsmget', 'op_instance': '6',
                                 'op_sequence': '15'},
                             {'op': 'hsmget', 'op_instance': '6',
                                 'op_sequence': '18'},
                             {'op': 'hsmget', 'op_instance': '6',
                                 'op_sequence': '21'},
                             {'op': 'hsmget', 'op_instance': '6',
                                 'op_sequence': '24'},
                             {'op': 'hsmget', 'op_instance': '7',
                                 'op_sequence': '13'},
                             {'op': 'hsmget', 'op_instance': '7',
                                 'op_sequence': '16'},
                             {'op': 'hsmget', 'op_instance': '7',
                                 'op_sequence': '19'},
                             {'op': 'hsmget', 'op_instance': '7',
                                 'op_sequence': '22'},
                             {'op': 'hsmget', 'op_instance': '7',
                                 'op_sequence': '25'},
                             {'op': 'mv', 'op_instance': '1', 'op_sequence': '33'},
                             {'op': 'mv', 'op_instance': '10', 'op_sequence': '60'},
                             {'op': 'mv', 'op_instance': '13', 'op_sequence': '69'},
                             {'op': 'mv', 'op_instance': '16', 'op_sequence': '74'},
                             {'op': 'mv', 'op_instance': '18', 'op_sequence': '83'},
                             {'op': 'mv', 'op_instance': '18', 'op_sequence': '86'},
                             {'op': 'mv', 'op_instance': '20', 'op_sequence': '84'},
                             {'op': 'mv', 'op_instance': '20', 'op_sequence': '87'},
                             {'op': 'mv', 'op_instance': '4', 'op_sequence': '42'},
                             {'op': 'mv', 'op_instance': '7', 'op_sequence': '51'},
                             {'op': 'ncatted', 'op_instance': '11',
                                 'op_sequence': '68'},
                             {'op': 'ncatted', 'op_instance': '12',
                                 'op_sequence': '73'},
                             {'op': 'ncatted', 'op_instance': '15',
                                 'op_sequence': '82'},
                             {'op': 'ncatted', 'op_instance': '15',
                                 'op_sequence': '85'},
                             {'op': 'ncatted', 'op_instance': '3',
                                 'op_sequence': '32'},
                             {'op': 'ncatted', 'op_instance': '5',
                                 'op_sequence': '41'},
                             {'op': 'ncatted', 'op_instance': '7',
                                 'op_sequence': '50'},
                             {'op': 'ncatted', 'op_instance': '9',
                                 'op_sequence': '59'},
                             {'op': 'ncrcat', 'op_instance': '10',
                                 'op_sequence': '62'},
                             {'op': 'ncrcat', 'op_instance': '12',
                                 'op_sequence': '71'},
                             {'op': 'ncrcat', 'op_instance': '13',
                                 'op_sequence': '76'},
                             {'op': 'ncrcat', 'op_instance': '2',
                                 'op_sequence': '26'},
                             {'op': 'ncrcat', 'op_instance': '4',
                                 'op_sequence': '35'},
                             {'op': 'ncrcat', 'op_instance': '6',
                                 'op_sequence': '44'},
                             {'op': 'ncrcat', 'op_instance': '8',
                                 'op_sequence': '53'},
                             {'op': 'rm', 'op_instance': '1', 'op_sequence': '27'},
                             {'op': 'rm', 'op_instance': '10', 'op_sequence': '54'},
                             {'op': 'rm', 'op_instance': '11', 'op_sequence': '61'},
                             {'op': 'rm', 'op_instance': '13', 'op_sequence': '63'},
                             {'op': 'rm', 'op_instance': '14', 'op_sequence': '70'},
                             {'op': 'rm', 'op_instance': '16', 'op_sequence': '75'},
                             {'op': 'rm', 'op_instance': '18', 'op_sequence': '77'},
                             {'op': 'rm', 'op_instance': '19', 'op_sequence': '88'},
                             {'op': 'rm', 'op_instance': '2', 'op_sequence': '34'},
                             {'op': 'rm', 'op_instance': '4', 'op_sequence': '36'},
                             {'op': 'rm', 'op_instance': '5', 'op_sequence': '43'},
                             {'op': 'rm', 'op_instance': '7', 'op_sequence': '45'},
                             {'op': 'rm', 'op_instance': '8', 'op_sequence': '52'},
                             {'op': 'splitvars', 'op_instance': '2',
                                 'op_sequence': '81'},
                             {'op': 'timavg', 'op_instance': '1',
                                 'op_sequence': '28'},
                             {'op': 'timavg', 'op_instance': '11',
                                 'op_sequence': '72'},
                             {'op': 'timavg', 'op_instance': '3',
                                 'op_sequence': '37'},
                             {'op': 'timavg', 'op_instance': '5',
                                 'op_sequence': '46'},
                             {'op': 'timavg', 'op_instance': '7',
                                 'op_sequence': '55'},
                             {'op': 'timavg', 'op_instance': '9',
                                 'op_sequence': '64'},
                             {'op': 'untar', 'op_instance': '2',
                                 'op_sequence': '29'},
                             {'op': 'untar', 'op_instance': '3',
                                 'op_sequence': '38'},
                             {'op': 'untar', 'op_instance': '4',
                                 'op_sequence': '47'},
                             {'op': 'untar', 'op_instance': '5',
                                 'op_sequence': '56'},
                             {'op': 'untar', 'op_instance': '6',
                                 'op_sequence': '65'},
                             {'op': 'untar', 'op_instance': '7', 'op_sequence': '78'}],
           'num_procs': 3480,
           'num_threads': 3668,
           'rdtsc_duration': -112126610546481758,
           'PERF_COUNT_SW_CPU_CLOCK': 86903088007,
           'write_bytes': 12254015488,
           'systemtime': 41980075,
           'invol_ctxsw': 20900,
           'rchar': 15458131996,
           'majflt': 8,
           'guest_time': 0,
           'read_bytes': 7000064,
           'usertime': 71155254,
           'inblock': 13672,
           'rssmax': 31621528,
           'time_waiting': 10152666725,
           'outblock': 23933624,
           'user+system': 113135329,
           'wchar': 15066048420,
           'minflt': 4972187,
           'delayacct_blkio_time': 0,
           'time_oncpu': 115330986461,
           'cancelled_write_bytes': 8925798400,
           'syscr': 2182175,
           'timeslices': 795433,
           'processor': 0,
           'syscw': 897834,
           'vol_ctxsw': 770843}

# Use samplej real job as template
# replace jobid with new number
# return list of limit of jobs
#def get_jobs(limit=None, fmt='df', offset=0):
def get_jobs(jobs = [], tags=None, fltr = None, order = None, limit = None, offset = 0, when=None, before=None, after=None, hosts=[], fmt='dict', annotations=None, analyses=None, merge_proc_sums=True, exact_tag_only = False):
    from datetime import datetime, timedelta
    # if offset >= limit: offset = limit
    if offset > 0:
        # This isn't quite right..
        # df[offset:offset+limit]
        limit = offset + limit
    logger.info("Getting jobs...Limit{} Offset{}".format(limit, offset))
    sample_component = '_annual_rho2_1x1deg'
    component_list = ['ocean','land','mountian']
    sample_name = '_historical'
    name_list = ['ESM0','ESM1']
    from copy import deepcopy
    result = []
    for n in range(limit):
        job = dict(samplej)
        job['jobid'] = str(1234000 + n)
        job['Processed'] = 1
        job['start'] = job['start'] + timedelta(days=n)
        job['end'] = job['end'] + timedelta(days=n)
        name = name_list[n%2]
        job['tags']['exp_name'] = name + sample_name
        if job['jobid'] == str(1234002):
            job['tags']['exp_name'] = "mismatch_test"
        comp = component_list[n%3] + sample_component
        job['tags']['exp_component'] = str(comp)
        result.append(deepcopy(job))
    return result[offset:]


# Job_gen does data cleanup and conversions for displaying
class job_gen:
    def __init__(self, limit=60, offset=0):
        import epmt_query as eq
        sample = eq.get_jobs(fmt='dict', limit=limit, offset=offset)

        self.df = pd.DataFrame(sample)
        self.df = self.df.sort_values(
                "start",  # Column to sort on
                ascending = False,  # Boolean eval.
                inplace=False
            )
        # Extract the exit code to a column
        exit_codes = [d.get('status')['exit_code'] for d in self.df.info_dict]
        self.df['exit_code'] = exit_codes
        self.df['Processed'] = 0
        # Extract tags out and merge them in as columns
        # tags = pd.DataFrame.from_dict(self.df['tags'].tolist())
        # self.df = pd.merge(self.df,tags, left_index=True, right_index=True)

        # Convert Job date into a start_day datetime date
        self.df['start_day'] = self.df.start.map(lambda x: x.date())
        # datetime.strptime(start, "%Y-%m-%d").date()

        # Select specific tags for displaying
        # logger.info("Tags{}".format(self.df['tags']))

        from .dash_config import columns_to_print
        self.df = self.df[columns_to_print]
        from json import dumps
        #self.df['tags'] = self.df['tags'].apply(dumps)
        # Convert True into 'Yes' for user friendly display
        import numpy as np
        self.df['Processed'] = np.where(self.df['Processed'], 'Yes', 'No')

        # User friendly column names
        self.df.rename(columns={
            'jobid': 'job id',
            'exit_code': 'exit status',
            'Processed': 'processing complete',
            'write_bytes': 'bytes_out',
            'read_bytes': 'bytes_in'
        }, inplace=True)

# ####################### End List of jobs ########################


# API Call
def comparable_job_partitions(jobs, matching_keys = ['exp_name', 'exp_component']):
    # Returns [ (('matchname','matchcomponent'), {set of matchjobids}), ...]

    # Typically jobids are only passed
    # I need to get the jobids name and component
    alt = job_gen().df[job_gen().df['job id'].isin(jobs)].reset_index()
    tags_df = pd.DataFrame.from_dict(alt['tags'].tolist())
    # Only Display Specific tags from dash_config
    tags_df = tags_df[['exp_name','exp_component']]
    # Dataframe of jobs
    #logger.debug(alt)
    # Dataframe of Tags of jobs
    #logger.debug(tags_df)
    alt = pd.merge(alt, tags_df, left_index=True, right_index=True)
    #alt.drop('tags',axis=1)
    # Now Calculate comparable jobs
    recs = alt.to_dict('records')
    cdict = {}
    for rec in recs:
        if (rec['exp_name'],rec['exp_component']) in cdict:
            cdict[(rec['exp_name'],rec['exp_component'])].update({rec['job id']})
        else:    
            cdict[(rec['exp_name'],rec['exp_component'])] = {str(rec['job id'])}
    # Reconfigure output format with out
    out = [ ((exp_name,exp_component),cdict[(exp_name,exp_component)]) for exp_name, exp_component in cdict]
    logger.debug(out)
    return out


# API Call
def detect_outlier_jobs(jobs, trained_model=None, features=['cpu_time', 'duration', 'num_procs'], methods=['modified_z_score'], thresholds='thresholds', sanity_check=True):
    """
    (df, parts) = eod.detect_outlier_jobs(jobs)
    pprint(parts)
    {'cpu_time': ([u'kern-6656-20190614-190245',
                   u'kern-6656-20190614-194024',
                   u'kern-6656-20190614-191138'],
                  [u'kern-6656-20190614-192044-outlier']),
     'duration': ([u'kern-6656-20190614-190245',
                   u'kern-6656-20190614-194024',
                   u'kern-6656-20190614-191138'],
                  [u'kern-6656-20190614-192044-outlier']),
     'num_procs': ([u'kern-6656-20190614-190245',
                    u'kern-6656-20190614-192044-outlier',
                    u'kern-6656-20190614-194024',
                    u'kern-6656-20190614-191138'],
                   [])}
    """
    returns = ('df', {'feature' : (['job','job2'], ['joboutlier'])})
    return "Running outlier analysis on Jobs: " + str(jobs)

df = pd.DataFrame()

def get_version():
    return "EPMT 1.1.1"
