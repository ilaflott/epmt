# settings.py
db_params = {'provider': 'sqlite', 'filename':'database.sqlite', 'create_db': True }
papiex_options = "PERF_COUNT_SW_CPU_CLOCK"
papiex_output = "/tmp/epmt/"
debug = False
input_pattern = "*-papiex-[0-9]*-[0-9]*.csv"
install_prefix = "../papiex-oss/papiex-oss-install/"
# DO NOT TOUCH THIS
metrics_offset = 12
