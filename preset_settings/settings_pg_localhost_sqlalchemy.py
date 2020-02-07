# Copy this file and edit it as follows:
# cp preset_settings/settings_xxxxxxx.py settings.py
# Then feel free to edit the file to suit you.

orm = 'sqlalchemy'
db_params = { 'url': 'postgresql://postgres:example@localhost:5432/EPMT', 'echo': False }
bulk_insert = True

# You can alter the settings below to override defaults
#
# jobid_env_list = [ "SLURM_JOB_ID", "SLURM_JOBID", "PBS_JOB_ID" ]
# papiex_options = "PERF_COUNT_SW_CPU_CLOCK"
# epmt_output_prefix = "/tmp/epmt/"
# stage_command = "mv"
# stage_command_dest = "./"
# verbose = 1
# input_pattern = "*-papiex-*-[0-9]*.csv"
# install_prefix = path.dirname(path.abspath(__file__)) + "/../papiex-oss/papiex-oss-install/"
# logfile = path.dirname(path.abspath(__file__)) + '/epmt.log'
#
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
# outlier_thresholds = { 'modified_z_score': 2.5, 'iqr': [20,80], 'z_score': 3.0 }
# outlier_features = ['duration', 'cpu_time', 'num_procs']
# # blacklist features for outlier detection. These will be skipped.
# # e.g, outlier_features_blacklist = ['rdtsc_duration', 'vol_ctxsw']
# outlier_features_blacklist = []
#
# data retention
# You will need to run `epmt retire` in a cron job for this to happen
# Remember, jobs that have dependent trained models will not be retired
# retire_jobs_ndays = 0   # specify in number of days; set to 0 to not retire jobs
# retire_models_ndays = 0 # specify in number of days; set to 0 to not retire models
#
#
#
#
# post_process_job_on_ingest = True

# to save post-processing compute cycles we only compute
# the process tree (parent/child, ancestor/descendant relations)
# when first needed. This also means the the process.inclusive_cpu_time
# will be unavailable until the process tree is computed.
# lazy_compute_process_tree = True
