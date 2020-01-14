# Copy this file and edit it as follows:
# cp preset_settings/settings_xxxxxxx.py settings.py
# Then feel free to edit the file to suit you.
from pathlib import Path
import os.path

orm = 'sqlalchemy'
db_params = { 'url': 'sqlite:///{HOME}/EPMT_DB.sqlite'.format(HOME=str(Path.home())), 'echo': False }
bulk_insert = True

# You can alter the settings below to override defaults
#
# jobid_env_list = [ "SLURM_JOB_ID", "SLURM_JOBID", "PBS_JOB_ID" ]
# papiex_options = "PERF_COUNT_SW_CPU_CLOCK"
# epmt_output_prefix = "/tmp/epmt/"
epmt_output_prefix = os.path.expandvars("$TMPDIR/epmt")
# stage_command = "mv"
# stage_command_dest = "./"
stage_command_dest = os.path.expandvars("/nbhome/$USER")
# verbose = 1
# input_pattern = "*-papiex-*-[0-9]*.csv"
install_prefix = "/home/Jeffrey.Durachta/workflowDB/EPMT/epmt-2.1.0-centos-6/papiex-epmt-install/"
# logfile = path.dirname(path.abspath(__file__)) + '/epmt.log'
#
# blacklist for environment filter (in addition to all keys with
# leading underscores)
# env_blacklist = ["LS_COLORS"]
#
# DO NOT EDIT BELOW UNLESS YOU KNOW WHAT YOU ARE DOING!
# #
# job_tags_env = 'EPMT_JOB_TAGS'
# per_process_fields = ["tags","hostname","exename","path","args","exitcode","pid","generation","ppid","pgid","sid","numtids"]
# skip_for_thread_sums = ["tid", "start", "end", "num_threads", "starttime"]
# all_tags_field = 'all_proc_tags'
# 
# # outlier detection
# outlier_thresholds = { 'modified_z_score': 2.5, 'iqr': [20,80], 'z_score': 3.0 }
# outlier_features = ['duration', 'cpu_time', 'num_procs']
# outlier_features_blacklist = ['user+system']
#
# post_process_job_on_ingest = True

# to save post-processing compute cycles we only compute
# the process tree (parent/child, ancestor/descendant relations)
# when first needed. This also means the the process.inclusive_cpu_time
# will be unavailable until the process tree is computed.
# lazy_compute_process_tree = True

