# settings.py
db_params = {'provider': 'postgres', 'user': 'postgres','password': 'example','host': 'localhost', 'dbname': 'EPMT'}
papiex_options = "PERF_COUNT_SW_CPU_CLOCK"
papiex_output = "/tmp/epmt/"
debug = False
input_pattern = "*-papiex-[0-9]*-[0-9]*.csv"
install_prefix = "../papiex-oss/papiex-oss-install/"
# DO NOT TOUCH BELOW THIS LINE
#
# metrics_offset = 12  ## not used any more
#
# we remove per_process_fields from the threads dataframe
# when computing sums for thread metrics, we fields mentioned in skip_for_thread_metric_sums
per_process_fields = ["tags","hostname","exename","path","args","exitcode","pid","generation","ppid","pgid","sid","numtids"]
skip_for_thread_metric_sums = ["tid", "start", "end", "num_threads"]

# tags
# delimiter separates one tag key/value pair from another
# separator separates the key-value within a par
# A tag should be like:
#   "app:TimeAvg;pprun:combine;runtime:100"
tag_delimiter = ';'
tag_kv_separator = ':'
tag_default_value = '1'

# query api
query_process_fields_exclude = ['threads_df']
# env_dict adds a lot of output, for now we skip returning it in queries
query_job_fields_exclude = ['env_dict']
