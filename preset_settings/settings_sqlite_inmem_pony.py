# Copy this file and edit it as follows:
# cp preset_settings/settings_xxxxxxx.py settings.py
# Then feel free to edit the file to suit you.

orm = 'pony'
db_params = { 'url': 'sqlite:///:memory:' }

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
#
# post_process_job_on_ingest = True
#
# Pony doesn't support bulk inserts
bulk_insert = False