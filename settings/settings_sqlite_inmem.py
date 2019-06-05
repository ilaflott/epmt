# settings.py
db_params = {'provider': 'sqlite', 'filename': ':memory:'}
jobid_env_list = [ "SLURM_JOB_ID", "SLURM_JOBID", "PBS_JOB_ID" ]
papiex_options = "PERF_COUNT_SW_CPU_CLOCK"
papiex_output = "/tmp/epmt/"
stage_command = "mv"
stage_command_dest = "./"
verbose = 1
input_pattern = "*-papiex-[0-9]*-[0-9]*.csv"
install_prefix = "../papiex-oss/papiex-oss-install/"
# DO NOT TOUCH BELOW THIS LINE
#
tag_kv_separator = ':'
tag_default_value = "1"
tag_delimiter = ';'
job_tags_env = 'EPMT_JOB_TAGS'
per_process_fields = ["tags","hostname","exename","path","args","exitcode","pid","generation","ppid","pgid","sid","numtids"]
skip_for_thread_sums = ["tid", "start", "end", "num_threads"]
query_process_fields_exclude = ['threads_df']
# query_job_fields_exclude = ['env_dict']
