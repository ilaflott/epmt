# EPMT

**Experiment Performance Management Tool**  aka  
**WorkflowDB** aka  
**PerfMiner**

This is a tool to collect metadata and performance data about an entire job down to the individual threads in individual processes. This tool uses **papiex** to perform the process monitoring. This tool is targeted at batch or ephemeral jobs, not daemon processes. 

The software contained in this repository was written by Philip Mucci of Minimal Metrics LLC.

## Table of Contents

[TOC]

## Verifying Installation 

It is best to check your installation and configuration using the ```epmt check``` command. Here is an example run from docker via the source tree. You will notice that we bind-mount the parent-directory of `epmt` to the container. This allows `epmt` to find the `papiex` install directory, lying adjacent to the `epmt` directory.

```
$ docker run --privileged -it --rm -v $PWD/..:/tmp/foo -w /tmp/foo/epmt python-epmt:latest ./epmt check
settings.db_params = {'filename': ':memory:', 'provider': 'sqlite'}
		   Pass
settings.install_prefix = ../papiex-oss/papiex-oss-install/
			ls -l ../papiex-oss/papiex-oss-install/bin/monitor-run>/dev/null
			ls -l ../papiex-oss/papiex-oss-install/lib/libpapiex.so>/dev/null
			ls -l ../papiex-oss/papiex-oss-install/lib/libmonitor.so>/dev/null
			ls -l ../papiex-oss/papiex-oss-install/lib/libpapi.so>/dev/null
			ls -l ../papiex-oss/papiex-oss-install/lib/libpfm.so>/dev/null
			ls -l ../papiex-oss/papiex-oss-install/bin/papi_command_line>/dev/null
			Pass
settings.papiex_output = /tmp/epmt/
		   mkdir -p /tmp/epmt/
		   mkdir -p /tmp/epmt/tmp
		   ls -lR /tmp/epmt/ >/dev/null
		   rm -rf /tmp/epmt/tmp
		   Pass
/proc/sys/kernel/perf_event_paranoid = 2
WARNING:epmt_cmds:restrictive /proc/sys/kernel/perf_event_paranoid value of 2, should be 0 for non-privileged users
			Pass
settings.papiex_options = PERF_COUNT_SW_CPU_CLOCK
			../papiex-oss/papiex-oss-install/bin/papi_component_avail| sed -n -e '/Active/,$p' | grep perf_event >/dev/null
			../papiex-oss/papiex-oss-install/bin/papi_command_line PERF_COUNT_SW_CPU_CLOCK| sed -n -e '/PERF_COUNT_SW_CPU_CLOCK\ :/,$p' | grep PERF_COUNT_SW_CPU_CLOCK > /dev/null
			Pass
WARNING:epmt_cmds:JOB_ID unset: Using session id 1 as JOB_ID
WARNING:epmt_cmds:JOB_NAME unset: Using job id 1 as JOB_NAME
WARNING:epmt_cmds:JOB_SCRIPTNAME unset: Using process name 1 as JOB_SCRIPTNAME
WARNING:epmt_cmds:JOB_USER unset: Using username root as JOB_USER
collect functionality (papiex+epmt)
	       epmt run -a /bin/sleep 1
	       Pass
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

Let's skip all the markup, as we can do it with only environment variables. **EPMT** can provide the configuration to export to the environment. The following example is for **BASH**.

The use for this is in a job file. **Please note the unset of LD_PRELOAD before stop:**

```
$ cat my_job_epmt_2.sh
#!/bin/bash
# Example job script for Torque or SLURM
# 
# Preamble, collect job metadata and monitor all processes/threads  
epmt start
export `epmt source`
#
./initialize_the_world --random 
./compute_the_world 
./postprocess_the_world 
#
# Postamble, disable monitoring and collect job metadata
unset LD_PRELOAD
epmt stop
```

The **unset LD_PRELOAD** line is to prevent the data collection routine from running on **epmt stop** itself.

When run interactively, **epmt source** just prints the required environment variables in **Bash** format:

```
$ epmt source
PAPIEX_OPTIONS=PERF_COUNT_SW_CPU_CLOCK LD_PRELOAD=../papiex-oss/papiex-oss-install/lib/libpapiex.so:../papiex-oss/papiex-oss-install/lib/libmonitor.so
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

To initialize a new session leader, consider using the **setsid** command. 

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
metrics_offset          12                                                      
papiex_options          PERF_COUNT_SW_CPU_CLOCK                                 
papiex_output           /tmp/epmt/                                              

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

## settings.py

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

**EPMT** can be passed noth **-n** (dry-run) and **-v** (verbosity) to help with debugging. Add more **-v** flags to increase the level of information printed.

```
$ epmt -v start
```

Or to attempt a submit without touching the database:

```
$ epmt -v -v -n submit /dir/to/jobdata
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

## EPMT under Docker 

Using the epmt-command docker image, we run **epmt** on a local directory to submit and set the submission DB host environment variable:

```
$ docker run --network=host -ti --rm -v `pwd`:/app -w /app -e EPMT_DB_HOST=<hostname> epmt-command:latest -v submit <localdir/>
```

This could be easilt aliased for convenience.

# Analysis of EPMT Data 

Current analytics are performed in an iPython notebook, specifically the SciPy-Notebook as described on [their homepage](https://jupyter-docker-stacks.readthedocs.io/en/latest/using/selecting.html).  

If you have Jupyter installed locally **and** you have installed the prerequisite Python modules (see **INSTALL.md**), there is no need to use the Docker image. You can simply load the **EPMT.ipynb** from the source directory in your environment and begin.

However, for those without an environment, using Docker (and assuming you build the images as described in **INSTALL.md**):

```
$ docker-compose up notebook
```

Follow the instructions printed to the screen to navigate to **EPMT.ipynb** or try this link [http://localhost:8888/notebooks/EPMT.ipynb]() and enter the encryption key. You must be in the directory where EPMT.ipynb exists when you start the notebook service. Further documentation exists in that file.

## Data Dictionary

EPMT collects data both from the job runtime and the applications run in that environment. See the **models/** directory for what fixed data is stored related to each object. Metric data is stored differently and the data collector's data directionary can be found in papiex-oss/README.md. At the time of this writing it looked like this:

```
Key                     Source							Description
-------------------------------------------------------------------------------------------------------------------------------------
exename			PAPI							Name of the application, usually argv[0]
path			PAPI							Path to the application
args			monitor							All arguments to the application not including argv[0]
pid			getpid()						Process id
generation		monitor 						Incremented after every exec()
ppid			getppid()						Parent process id
pgid			getpgid()						Process group id
sid			getsid()						Process session id
numtids			monitor							Number of threads caught by instrumentation
tid			gettid()						Thread id
start			gettimeofday() 						Microsecond timestamp at start
end			gettimeofday() 						Microsecond timestamp at end
usertime		getrusage(RUSAGE_THREAD) 				Microsecond user time 
systemtime		getrusage(RUSAGE_THREAD) 				Microsecond system time
rssmax			getrusage(RUSAGE_THREAD) 				Kb max resident set size
minflt			getrusage(RUSAGE_THREAD) 				Minor faults (TLB misses/new page frames)
majflt			getrusage(RUSAGE_THREAD) 				Major page faults (requiring I/O)
inblock			getrusage(RUSAGE_THREAD) 				512B blocks read from I/O 
outblock		getrusage(RUSAGE_THREAD) 				512B blocks written to I/O 
vol_ctxsw		getrusage(RUSAGE_THREAD) 				Boluntary context switches (yields)
invol_ctxsw		getrusage(RUSAGE_THREAD) 				Involuntary context switches (preemptions)
num_threads		/proc/<pid>/task/<tid>/stat field 20 	     	 	Threads in process at finish
starttime		/proc/<pid>/task/<tid>/stat field 22 	     	      	Timestamp in jiffies after boot thread was started
processor		/proc/<pid>/task/<tid>/stat field 39 	     	      	CPU this thread last ran on
delayacct_blkio_time	/proc/<pid>/task/<tid>/stat field 42 	     	      	Jiffies process was blocked in D state on I/O device
guest_time		/proc/<pid>/task/<tid>/stat field 43 	     	      	Jiffies running a virtual CPU for a guest OS
rchar			/proc/<pid>/task/<tid>/io line 1  		      	Bytes read via syscall (may come from pagecache not I/O device)
wchar			/proc/<pid>/task/<tid>/io line 2  		      	Bytes written via syscall (may go to pagecache not I/O device)
syscr			/proc/<pid>/task/<tid>/io line 3  		      	Read syscalls 
syscw			/proc/<pid>/task/<tid>/io line 4  		      	Write syscalls
read_bytes		/proc/<pid>/task/<tid>/io line 4  		      	Bytes read from I/O device
write_bytes		/proc/<pid>/task/<tid>/io line 4  		      	Bytes written to I/O device
cancelled_write_bytes	/proc/<pid>/task/<tid>/io line 4  		      	Number of bytes discarded by truncation
time_oncpu		/proc/<pid>/task/<tid>/schedstat		      	Time in jiffies spent running the CPI
time_waiting		/proc/<pid>/task/<tid>/schedstat		      	Time in jiffies waiting for a run queue while runnable
timeslices		/proc/<pid>/task/<tid>/schedstat		      	Number of run periods on CPU
rdtsc_duration		<Hardware RDTSC>				      	Real time cycle counter duration of thread
```

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

Note that often in virtual environments, hardware counters are not often available in the VM. 
