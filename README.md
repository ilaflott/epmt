# EPMT

Experiment Performance Management Tool a.k.a Workflow DB

This is a tool to collect metadata and performance data about an entire job down to the individual threads in individual processes. This tool uses **papiex** to perform the process monitoring. This tool is targeted at batch or ephemeral jobs, not daemon processes. 

Questions/Comments to the Author: *phil@minimalmetrics.com*

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

When run interactively, **epmt source** just prints the required environment variables:

```
$ epmt source
PAPIEX_OPTIONS=PERF_COUNT_SW_CPU_CLOCK LD_PRELOAD=../papiex-oss/papiex-oss-install/lib/libpapiex.so:../papiex-oss/papiex-oss-install/lib/libmonitor.so
```

But it's real use is in a job file. **Please note the unset of LD_PRELOAD before stop:**

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

```epmt submit <dir>/*tgz```

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

## Configuration

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

## Debugging

**EPMT** can be passed noth **-n** (dry-run) and **-v** (verbosity) to help with debugging. Add more **-v** flags to increase the level of information printed.

```
$ epmt -v start
```

Or to attempt a submit without touching the database:

```
$ epmt -v -v -n submit /dir/to/jobdata
```
 
Another useful feature is to just use the in-memory SqlLite database, which allows full submit and query testing. There are two prebuilt settings files for this.


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

Lets run epmt on a local directory to submit and set the submission DB host environment variable:

```
docker run --network=host -ti --rm -v `pwd`:/app -w /app -e EPMT_DB_HOST=<hostname> epmt-command:latest -v submit <localdir/>
```
## Testing Python Versions under Docker

One can test **EPMT** on various versions of python with the following make commands. Each will test against a minimal install of Python, without installing any dependencies. This should work for **start, stop, dump, help and submit, the latter with -n or --dry-run**. 

```
make check-python-native
make check-python-2.6
make check-python-2.7
make check-python-3
```

Python 3 support is not yet available.

