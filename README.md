# EPMT

**Experiment Performance Management Tool**  aka  
**WorkflowDB** aka  
**PerfMiner**

This is a tool to collect metadata and performance data about an entire job down to the individual threads in individual processes. This tool uses **papiex** to perform the process monitoring. This tool is targeted at batch or ephemeral jobs, not daemon processes. 

The software contained in this repository was written by Philip Mucci of Minimal Metrics LLC.

## Verifying Installation 

It is best to check your installation and configuration using the ```epmt check``` command.

Here is an example:
```
$ epmt check
settings.db_params = {'url': 'sqlite:////home/chris/EPMT_DB_2.2.7.sqlite', 'echo': False}       Pass
settings.install_prefix = /home/chris/Downloads/epmt-2.2.7/papiex-epmt-install/ Pass
settings.epmt_output_prefix = /tmp/epmt/        Pass
/proc/sys/kernel/perf_event_paranoid =  0       Pass
settings.papiex_options = PERF_COUNT_SW_CPU_CLOCK       Pass
epmt stage functionality        Pass
WARNING:epmtlib:No job name found, defaulting to unknown
epmt run functionality  Pass
```

We have a comprehensive set of unit tests. The epmt unittest command will begin those tests:
```
$ epmt unittest


Running test.test_lib
test_dict_filter (test.test_lib.EPMTLib) ... ok
test_merge_intervals (test.test_lib.EPMTLib) ... ok
test_sqlite_json_support (test.test_lib.EPMTLib) ... ok
test_url_to_db_params (test.test_lib.EPMTLib) ... ok

----------------------------------------------------------------------
Ran 4 tests in 0.086s

OK
....

OK
All tests successfully PASSED
```

## Modes of EPMT

There are three modes to **EPMT** usage, collection, submission and analysis, and have an increasing number of dependencies:

* **Collection** only requires a minimal Python installation of 2.6.x or higher
* **Submission** requires Python packages for data and database interaction
* **Analysis** requires [Jupyter](https://jupyter.org), an iPython notebook environment, as well as additional python data analysis libraries.

#### Configuration
  
All three modes reference the **settings.py** file as well as **environment variables**. EPMT uses uses a in-memory, temporary database by default, see **Configuring a Database**.  

```text
 $ cat settings.py
 db_params = {'provider': 'sqlite', 'filename': ':memory:'}
 papiex_options = "PERF_COUNT_SW_CPU_CLOCK"
 epmt_output_prefix = "/tmp/epmt/"
 debug = False
 input_pattern = "*-papiex-[0-9]*-[0-9]*.csv"
 install_prefix = "../papiex-oss/papiex-oss-install/"
 # DO NOT TOUCH THIS
```

### Collection


Automatic **Collection** with SLURM
---

Using configured prolog and epilogs with SLURM tasks allows one to skip job instrumentation entirely, with the exception of job tags (***EPMT_JOB_TAGS***) and process tags (***PAPIEX_TAGS***). These are configured in `slurm.conf` for jobs submitted with `sbatch` but they can be tested on the command line when using `srun`. 

The above Csh job is equivalent to the below sequence using a prolog and epilog, ***with the exception of the trailing submit statement.***

```
srun -n1 \\
--task-prolog=$EPMT_PREFIX/epmt-install/slurm/slurm_task_prolog_epmt.sh \\
--task-epilog=$EPMT_PREFIX/epmt-install/slurm/slurm_task_epilog_epmt.sh \\
sleep 1
```

For this job to work using `sbatch` the following modifications in the `slurm.conf` would be made, substituting the appropriate path for EPMT_PREFIX:

```
TaskProlog=EPMT_PREFIX/epmt-install/slurm/slurm_task_prolog_epmt.sh
TaskEpilog=EPMT_PREFIX/epmt-install/slurm/slurm_task_epilog_epmt.sh
```

If this fails, then it's likely the papiex installation is either missing or misconfigured in **settings.py**. The **-a** flag tells **EPMT** to treat this run as an entire **job**. See **README.md** for further details.

### Submission
---

We can submit our previous job to the database defined in **settings.py** just run the epmt submit command with the directory returned by stage (found in location set by settings.py epmt_output_prefix):

```text
$ epmt -v submit /tmp/epmt/1/
INFO:epmt_cmds:submit_to_db(/tmp/epmt/1/,*-papiex-[0-9]*-[0-9]*.csv,False)
INFO:epmt_cmds:Unpickling from /tmp/epmt/1/job_metadata
INFO:epmt_cmds:1 files to submit
INFO:epmt_cmds:1 hosts found: ['linuxkit-025000000001-']
INFO:epmt_cmds:host linuxkit-025000000001-: 1 files to import
INFO:epmt_job:Binding to DB: {'filename': ':memory:', 'provider': 'sqlite'}
INFO:epmt_job:Generating mapping from schema...
INFO:epmt_job:Processing job id 1
INFO:epmt_job:Creating user root
INFO:epmt_job:Creating job 1
INFO:epmt_job:Creating host linuxkit-025000000001-
INFO:epmt_job:Creating metricname usertime
INFO:epmt_job:Creating metricname systemtime
INFO:epmt_job:Creating metricname rssmax
INFO:epmt_job:Creating metricname minflt
INFO:epmt_job:Creating metricname majflt
INFO:epmt_job:Creating metricname inblock
INFO:epmt_job:Creating metricname outblock
INFO:epmt_job:Creating metricname vol_ctxsw
INFO:epmt_job:Creating metricname invol_ctxsw
INFO:epmt_job:Creating metricname num_threads
INFO:epmt_job:Creating metricname starttime
INFO:epmt_job:Creating metricname processor
INFO:epmt_job:Creating metricname delayacct_blkio_time
INFO:epmt_job:Creating metricname guest_time
INFO:epmt_job:Creating metricname rchar
INFO:epmt_job:Creating metricname wchar
INFO:epmt_job:Creating metricname syscr
INFO:epmt_job:Creating metricname syscw
INFO:epmt_job:Creating metricname read_bytes
INFO:epmt_job:Creating metricname write_bytes
INFO:epmt_job:Creating metricname cancelled_write_bytes
INFO:epmt_job:Creating metricname time_oncpu
INFO:epmt_job:Creating metricname time_waiting
INFO:epmt_job:Creating metricname timeslices
INFO:epmt_job:Creating metricname rdtsc_duration
INFO:epmt_job:Creating metricname PERF_COUNT_SW_CPU_CLOCK
INFO:epmt_job:Adding 1 processes to job
INFO:epmt_job:Earliest process start: 2019-03-06 15:36:56.948350
INFO:epmt_job:Latest process end: 2019-03-06 15:37:06.996065
INFO:epmt_job:Computed duration of job: 10047715.000000 us, 0.17 m
INFO:epmt_job:Staged import of 1 processes, 1 threads
INFO:epmt_job:Staged import took 0:00:00.189151, 5.286781 processes per second
INFO:epmt_cmds:Committed job 1 to database: Job[u'1']
```

## Analysis and Visualization
---

EPMT Uses a **ipython notebook** data analytics environment.  Starting the jupyter notebook is easy from the **epmt notebook** command.

```text
$ epmt notebook
[I 15:39:24.236 NotebookApp] Serving notebooks from local directory: /home/chris/Documents/playground/MM/build/epmt
[I 15:39:24.236 NotebookApp] The Jupyter Notebook is running at:
[I 15:39:24.236 NotebookApp] http://localhost:8888/?token=9c7529e19e12cb8121d66ff471e96fdd3056f6acc4480274
[I 15:39:24.236 NotebookApp]  or http://127.0.0.1:8888/?token=9c7529e19e12cb8121d66ff471e96fdd3056f6acc4480274
[I 15:39:24.236 NotebookApp] Use Control-C to stop this server and shut down all kernels (twice to skip confirmation).
[C 15:39:24.263 NotebookApp] 
    
    To access the notebook, open this file in a browser:
        file:///home/chris/.local/share/jupyter/runtime/nbserver-18690-open.html
    Or copy and paste one of these URLs:
        http://localhost:8888/?token=9c7529e19e12cb8121d66ff471e96fdd3056f6acc4480274
     or http://127.0.0.1:8888/?token=9c7529e19e12cb8121d66ff471e96fdd3056f6acc4480274
```

The notebook command offers passing paramaters to jupyter such as host IP for sharing access to the notebook with machines on the local network, notebook token and notebook password
```
$ epmt notebook -- --ip 0.0.0.0 --NotebookApp.token='thisisatoken' --NotebookApp.password='hereisa$upersecurepassword'
```


## Collecting Performance Data

Assuming you have EPMT installed and in your path, let's modify a job file:

```
$ cat my_job.sh
#!/bin/bash
# Example job script for Torque or SLURM
./compute_the_world --debug 
```

This becomes:

```
$ cat my_job_epmt.sh
#!/bin/bash
# Example job script for Torque or SLURM
epmt start
epmt run ./compute_the_world --debug 
epmt stop
```

Or more succintlty by automating the start/stop cycle with the **--auto** or **-a** flag:  

```
$ cat my_job_epmt2.sh
#!/bin/bash
# Example job script for Torque or SLURM
epmt -a run ./compute_the_world --debug
```

But usually we want to run more than one executable. We could have any number of run statements:

```
$ cat my_job_epmt3.sh
#!/bin/bash
# Example job script for Torque or SLURM
#
epmt start
epmt run ./initialize_the_world --random 
epmt run ./compute_the_world 
epmt run ./postprocess_the_world 
epmt stop
```

Let's skip all the markup, as we can do it with only environment variables. **EPMT** provides the configuration to export to the environment through the **source** command. The use for this is in a job file and is meant to be evaluated by the running shell, be that some form of Bash or Csh. **epmt source** just prints the required environment variables in Bash format **unless either the "SHELL" or "_" environment variable ends in csh**. 

**Note the unset of LD_PRELOAD before stop!** This line is to prevent the data collection routine from running on **epmt stop** itself.

```
$ cat my_job_bash.sh
#!/bin/bash
# Example job script for Torque or SLURM
 
### Preamble, collect job metadata and monitor all processes/threads  
epmt start
eval `epmt source`
#
./initialize_the_world --random 
./compute_the_world 
./postprocess_the_world 
#
# Postamble, disable monitoring and collect job metadata
unset LD_PRELOAD
epmt stop
```

Here's an example for Csh, when run interactively, 


```
$ /bin/csh
> epmt -j1 source
setenv PAPIEX_OPTIONS PERF_COUNT_SW_CPU_CLOCK;
setenv PAPIEX_OUTPUT /tmp/epmt/1/;
setenv LD_PRELOAD /Users/phil/Work/GFDL/epmt.git/../papiex-oss/papiex-oss-install/lib/libpapiex.so:/Users/phil/Work/GFDL/epmt.git/../papiex-oss/papiex-oss-install/lib/libpapi.so:/Users/phil/Work/GFDL/epmt.git/../papiex-oss/papiex-oss-install/lib/libpfm.so:/Users/phil/Work/GFDL/epmt.git/../papiex-oss/papiex-oss-install/lib/libmonitor.so
```

## Importing Data Into the Database

After collecting the data, jobs (groups of processes) are imported into the database with the **submit** command. This command takes arguments in the form of directories or tar files that must contain a *job_metadata* file.   

Normal operation is to submit one or more directories:

```epmt submit <dir1/> [...]```

One can also submit a list of compressed tar files:

```epmt submit <compressed_dir_file.*z> [...]```

There is also a mode where the current environment is used to determine where to find the data.

```epmt submit```


### Examples

#### Submitting a directory of compressed job data

This might happen at the end of the day via a cron job:

```
$ epmt submit <dir>/*tgz
```

### Submitting data directly from within a job

These commands could be part of every users job, or in the batch systems configurable preambles/postambles.

```
$ cat my_job.sh
#!/bin/bash
# Example job script for Torque or SLURM
echo "$PBS_JOBID or $SLURM_JOBID"
epmt start
epmt run ./compute_the_world --debug 
epmt stop
epmt submit

```


The start/stop cycle can be removed with the **--auto** or **-a** flag, which performs start and stop for you.  

```
$ epmt -a run ./debug_the_world --outliers
$ epmt submit
```

### Submitting data from the current session

If not inside of a batch environment, **epmt** will *attempt to fake-and-bake a job id*. This is quite useful when just performing interactive runs. **Note you may not be able to submit these jobs to a shared database. The session ID is not guaranteed to be unique across reboots, much less other systems** However, this use case is perfectly acceptable when using a private database.

```
$ epmt start
WARNING:epmt_cmds:JOB_ID unset: Using session id 6948 as JOB_ID
WARNING:epmt_cmds:JOB_NAME unset: Using job id 6948 as JOB_NAME
WARNING:epmt_cmds:JOB_SCRIPTNAME unset: Using process name 6948 as JOB_SCRIPTNAME
WARNING:epmt_cmds:JOB_USER unset: Using username phil as JOB_USE$ epmt run ./debug_the_world --outliers
$ epmt stop
$ epmt submit
```

## Usage and Configuration

**EPMT** gets all of it's configuration from two places, environment variables and the **settings.py** file. One can examine all the current settings by passing the **--help** option.

```
$ ./epmt help
usage: epmt [-n] [-d] [-h] [-a] [--drop]
            [epmt_cmd] [epmt_cmd_args [epmt_cmd_args ...]]

positional arguments:
  epmt_cmd       start, run, stop, submit, dump
  epmt_cmd_args  Additional arguments, command dependent

optional arguments:
  -n, --dry-run  Don't touch the database
  -v, --verbose  Increase level of verbosity/debug
  -h, --help     Show this help message and exit
  -a, --auto     Do start/stop when running
  --drop         Drop all tables/data and recreate before importing

settings.py (overridden by below env. vars):
db_params               {'host': 'localhost', 'password': 'example', 'user': 'postgres', 'dbname': 'EPMT', 'provider': 'postgres'}
debug                   False                                                   
input_pattern           *-papiex-[0-9]*-[0-9]*.csv                              
install_prefix          ../papiex-oss/papiex-oss-install/                       
papiex_options          PERF_COUNT_SW_CPU_CLOCK                                 
epmt_output_prefix      /tmp/epmt/                                              

environment variables (overrides settings.py):
```

## Environment Variables

The following variables replace, at run-time, the values in the **db_params** dictionary found in **settings.py**.

```
EPMT_DB_PROVIDER
EPMT_DB_USER
EPMT_DB_PASSWORD
EPMT_DB_HOST
EPMT_DB_DBNAME
EPMT_DB_FILENAME
```

### settings.py

There are a number of example files provided. See **INSTALL.md** for more details.

```
$ ls settings
settings_pg_container.py	settings_sqlite_inmem.py
settings_pg_localhost.py	settings_sqlite_localfile.py
$
$ # In memory only, disappears after run
$ cp /path/to/install/settings/settings_sqlite_inmem.py /path/to/install/settings.py
$ 
$ # Persistent and on disk
$ cp /path/to/install/settings/settings_sqlite_localfile.py /path/to/install/settings.py
$ epmt -v -v submit /dir/to/jobdata
```

## Debugging

**EPMT** can be passed both **-n** (dry-run) and **-v** (verbosity) to help with debugging. Add more **-v** flags to increase the level of information printed **-vvv**.

```
$ epmt -v start
```

Or to attempt a submit without touching the database:

```
$ epmt -vv submit -n /dir/to/jobdata
```

Also, one can decode and dump the job_metadata file in a dir or compressed dir.

```
$ epmt dump ~/Downloads/yrs05-25.20190221/CM4_piControl_C_atmos_00050101.papiex.gfdl.19712961.tgz 
exp_component           atmos                                                   
exp_jobname             CM4_piControl_C_atmos_00050101                          
exp_name                CM4_piControl_C                                         
exp_oname               00050101                                                
job_el_env_changes      {}                                                      
job_el_env_changes_len  0                                                       
job_el_from_batch       []                                                      
job_el_status           0                                                       
job_el_stop             2019-02-20 22:13:23.131187                              
job_pl_env              {'LANG': 'en_US', 'PBS_QUEUE': 'batch', 'SHELL': '/bin/csh', 'PBS_ENVIRONMENT': 'PBS_BATCH', 'PAPIEX_TAGS': 'atmos', 'SHLVL': '3', 'PBS_WALLTIME': '216000', 'MOAB_NODELIST': 'pp057.princeton.rdhpcs.noaa.gov', 'PBS_VERSION': 'TORQUE-6.0.2', 'PAPIEX_OUTPUT': '/vftmp/Foo.Bar/pbs20345339/papiex',  'LOADEDMODULES': '', 'LC_TIME': 'C', 'MACHTYPE': 'x86_64', 'PAPIEX_OPTIONS': 'PERF_COUNT_SW_CPU_CLOCK', 'MOAB_GROUP': 'f'}
job_pl_env_len          81                                                      
job_pl_from_batch       []                                                      
job_pl_groupnames       ['f', 'f']                                              
job_pl_hostname         pp057                                                   
job_pl_id               20345339.moab01.princeton.rdhpcs.noaa.gov               
job_pl_jobname          CM4_piControl_C_atmos_00050101                          
job_pl_scriptname       CM4_piControl_C_atmos_00050101                          
job_pl_start            2019-02-20 19:58:41.274267                              
job_pl_submit           2019-02-20 19:58:41.274463                              
job_pl_username         Foo.Bar                                        

```


## Performance Metrics Data Dictionary

EPMT collects data both from the job runtime and the applications run in that environment. See the **models/** directory for what fixed data is stored related to each object. Metric data is stored differently and the data collector's data directionary can be found in papiex-oss/README.md. At the time of this writing it looked like this:


| Key                       	| Scope   	| Description                                            	|
|---------------------------	|---------	|--------------------------------------------------------	|
| 1. tags                   	| Process 	| User specified tags for this executable                	|
| 2. hostname               	| Process 	| hostname                                               	|
| 3. exename                	| Process 	| Name of the application, usually argv[0]               	|
| 4. path                   	| Process 	| Path to the application                                	|
| 5. args                   	| Process 	| All arguments to exe excluding argv[0]                 	|
| 6. exitcode               	| Process 	| Exit code                                              	|
| 7. exitsignal             	| Process 	| Exited due to a signal                                 	|
| 8. pid                    	| Process 	| Process id                                             	|
| 9. generation             	| Process 	| Incremented after every exec() or PID wrap             	|
| 10. ppid                  	| Process 	| Parent process id                                      	|
| 11. pgid                  	| Process 	| Process group id                                       	|
| 12. sid                   	| Process 	| Process session id                                     	|
| 13. numtids               	| Process 	| Number of threads caught by instrumentation            	|
| 14. numranks              	| Process 	| Number of MPI ranks detected                           	|
| 15. tid                   	| Process 	| Thread id                                              	|
| 16. mpirank               	| Thread  	| MPI rank                                               	|
| 17. start                 	| Process 	| Microsecond timestamp at start                         	|
| 18. end                   	| Process 	| Microsecond timestamp at end                           	|
| 19. usertime              	| Thread  	| Microsecond user time                                  	|
| 20. systemtime            	| Thread  	| Microsecond system time                                	|
| 21. rssmax                	| Thread  	| Kb max resident set size                               	|
| 22. minflt                	| Thread  	| Minor faults (TLB misses/new page frames)              	|
| 23. majflt                	| Thread  	| Major page faults (requiring I/O)                      	|
| 24. inblock               	| Thread  	| 512B blocks read from I/O                              	|
| 25. outblock              	| Thread  	| 512B blocks written to I/O                             	|
| 26. vol_ctxsw             	| Thread  	| Voluntary context switches (yields)                    	|
| 27. invol_ctxsw           	| Thread  	| Involuntary context switches (preemptions)             	|
| 28. cminflt               	| Process 	| minflt (20) for all wait()ed children                  	|
| 29. cmajflt               	| Thread  	| majflt (21) for all wait()ed children                  	|
| 30. cutime                	| Process 	| utime (17) for all wait()ed children                   	|
| 31. cstime                	| Thread  	| stime (18) for all wait()ed children                   	|
| 32. num_threads           	| Process 	| Threads in process at finish                           	|
| 33. starttime             	| Thread  	| Timestamp in jiffies after boot thread was started     	|
| 34. processor             	| Thread  	| CPU this thread last ran on                            	|
| 35. delayacct_blkio_time  	| Thread  	| Jiffies process blocked in D state on I/O device       	|
| 36. guest_time            	| Thread  	| Jiffies running a virtual CPU for a guest OS           	|
| 37. rchar                 	| Thread  	| Bytes read via syscall (maybe from cache not dev I/O)  	|
| 38. wchar                 	| Thread  	| Bytes written via syscall (maybe to cache not dev I/O) 	|
| 39. syscr                 	| Thread  	| Read syscalls                                          	|
| 40. syscw                 	| Thread  	| Write syscalls                                         	|
| 41. read_bytes            	| Thread  	| Bytes read from I/O device                             	|
| 42. write_bytes           	| Thread  	| Bytes written to I/O device                            	|
| 43. cancelled_write_bytes 	| Thread  	| Bytes discarded by truncation                          	|
| 44. time_oncpu            	| Thread  	| Nanoseconds spent running                              	|
| 45. time_waiting          	| Thread  	| Nanoseconds runnable but waiting                       	|
| 46. timeslices            	| Thread  	| Number of run periods on CPU                           	|
| 47. rdtsc_duration        	| Thread  	| If PAPI, real time cycle duration of thread            	|
| *                         	| Thread  	| PAPI metrics                                           	|

### Addition of new metrics

Additional metrics can be configured either in two ways:
* The papiex_options string In **settings.py** if using ```epmt run``` or ```epmt source```
* The value of the **PAPIEX_OPTIONS** environment variable if using ```LD_PRELOAD``` directly.

The value of these should be a comma separated string:
```
$ export PAPIEX_OPTIONS="PERF_COUNT_SW_CPU_CLOCK,PAPI_CYCLES"
```

To list available and functioning metrics, use one of the included command line tools:
 * papi_avail
 * papi_native_avail
 * check_events (libpfm)
 * showevtinfo (libpfm)
 * perf list (linux)

**The PERF_COUNT_SW_* events should work on any system that has the proper /proc/sys/kernel/perf_event_paranoid setting**.

One should verify the functionality of the metric using the ```papi_command_line``` tool:

```
$ papi_command_line PERF_COUNT_SW_CPU_CLOCK

$ papi_command_line CYCLES

```


## Troubleshooting

### Error: `version GLIBC_x.xx not found`

The collector library may not have been built for the current environment or the release
OS version does not match the current environment. 

### Virtual Environments:
Note that often in virtual environments, hardware counters are not often available in the VM. 