from getpass import getuser
from os import path


def test_settings_import():
    pass


# Copy this file and edit it as follows:
# cp preset_settings/settings_xxxxxxx.py settings.py
# Then feel free to edit the file to suit you.

orm = 'sqlalchemy'
db_params = {'url': 'postgresql://postgres:example@postgres:5432/EPMT', 'echo': False}
bulk_insert = True

# You can alter the settings below to override defaults
#
# jobid_env_list = [ "SLURM_JOB_ID", "SLURM_JOBID", "PBS_JOB_ID" ]
# papiex_options = "PERF_COUNT_SW_CPU_CLOCK,COLLATED_TSV"
# epmt_output_prefix = "/tmp/epmt/"
# stage_command = "mv"
# stage_command_dest = "./"
# verbose = 0
# input pattern must match both csv v1 and v2 filenames
# input_pattern = "*-papiex*.[ct]sv"
# install_prefix = path.dirname(path.abspath(__file__)) + "/../papiex-oss/papiex-epmt-install/"

# when we are not attached to a terminal we log to the file below
# logfile = path.expandvars("/tmp/epmt_{}.log".format(getuser() or "unknown"))

# blacklist for environment filter (in addition to all keys with
# leading underscores)
# env_blacklist = ["LS_COLORS"]
#
# DO NOT EDIT BELOW UNLESS YOU KNOW WHAT YOU ARE DOING!
# #
# job_tags_env = 'EPMT_JOB_TAGS'
# per_process_fields = ["tags","hostname","exename","path","args","exitcode","pid","generation","ppid","pgid","sid","numtids", "mpinumranks", "mpirank", "exitsignal"]
# skip_for_thread_sums = ["tid", "start", "end", "num_threads", "starttime"]
#
# # outlier detection
# univariate_classifiers = ['iqr', 'modified_z_score', 'z_score']
# outlier_thresholds = { 'modified_z_score': 3.5, 'z_score': 3.0 }
# outlier_features = ['duration', 'cpu_time', 'num_procs']
# # blacklist features for outlier detection. These will be skipped.
# outlier_features_blacklist = ['env_dict', 'tags', 'info_dict', 'env_changes_dict', 'annotations', 'analyses', 'jobid', 'jobname', 'user', 'all_proc_tags', 'created_at', 'modified_at', 'start', 'end']
#
# data retention
# You will need to run `epmt retire` in a cron job for this to happen
# Remember, jobs that have dependent trained models will not be retired
# retire_jobs_ndays = 0   # specify in number of days; set to 0 to not retire jobs
# retire_models_ndays = 0 # specify in number of days; set to 0 to not retire models
#
#
post_process_job_on_ingest = True

# to save post-processing compute cycles we only compute
# the process tree (parent/child, ancestor/descendant relations)
# when first needed. This also means the the process.inclusive_cpu_time
# will be unavailable until the process tree is computed.
lazy_compute_process_tree = True

epmt_settings_kind = 'pg_container_sqlalchemy'
