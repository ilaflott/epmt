# settings.py
db_params = {'provider': 'sqlite', 'filename': ':memory:'}
jobid_env_list = [ "SLURM_JOB_ID", "SLURM_JOBID", "PBS_JOB_ID" ]
papiex_options = "PERF_COUNT_SW_CPU_CLOCK"
papiex_output = "/tmp/epmt/"
stage_command = "mv"
stage_command_dest = "./"
verbose = 1
input_pattern = "*-papiex-[0-9]*-[0-9]*.csv"
install_prefix = "/opt/papiex/"
# DO NOT TOUCH THIS
metrics_offset = 12
tag_kv_separator = ':'
tag_default_value = "1"
tag_delimiter = ';'
job_tags_env = 'EPMT_JOB_TAGS'
per_process_fields = ["tags","hostname","exename","path","args","exitcode","pid","generation","ppid","pgid","sid","numtids"]
skip_for_thread_sums = ["tid", "start", "end", "num_threads"]
