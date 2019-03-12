# For Delivery

Default data collected
Document configuration of settings.py
Adding/changing PERF events
What happens if error

# Todo

Consider recording argv[0] as well
Add duration to metric array (fix and import)
Add 2 boxplots for reference data vs cleaned reference data for metric
Add boxplots/scatter plot for cleaned data with outliers
Fix quantile computation for filtering
Normalize times/metrics?
Merge files before import?
Add units and scale to metrics
Abstract all metrics from object for easy fetch
Add object mixins for manipulations
Store object data as dataframes in JSON?
Version all data structures (CSV, Dicts, Schema)
Use migration branch of Pony
Make summary or computable object
Add function/object documentation
Add dict support for start/stop/run (info_dict)
Manage transaction logging
Managing unique submission of processes to jobs
Manage .tgz handling better, single get_member/extract pass
Fix environment variable vs. settings
Identical job ID's with different usernames?
Fix leaking usernames on bad job commit
Turn metrics into MetricArray/MetricSet
Add submit time to metadata and database, check env
Add config command to change settings
Fix settings handling
Fix global variable handling
Fix environment variable handling (PAPIEX_OPTIONS, PAPIEX_DEBUG, PAPIEX_OUTPUT, PAPIEX_INSTALL?)
Make install target and Python virtual environment
Outlier detection and averaging
- Allow multiple methods
  - Quartiles
  - N * (X-mu/stddev)
- Reduce single queries
- Use bulk Pandas processing

# Bugs

- Deleting a job, CASCADE?

# Performance

- Job import time

# EPMT Functionality

Additional command line options:
- List hardware events
- List data dictionary for collection and for job
- List job(s) 
- Delete job(s)
- Database check
- Collector check
- PAPIEX check
- Config settings.py
