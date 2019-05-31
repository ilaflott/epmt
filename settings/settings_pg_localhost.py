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
