# settings.py
db_params = {'provider': 'postgres', 'user': 'postgres','password': 'example','host': 'localhost', 'dbname': 'EPMT'}
PAPIEX_OPTIONS = "PERF_COUNT_SW_CPU_CLOCK"
debug = False
input_pattern = "*-papiex-[0-9]*-[0-9]*.csv"
output_prefix = "/tmp/epmt/"
install_prefix = "../papiex-oss/papiex-oss-install/"
# DO NOT TOUCH THIS
metrics_offset = 12

