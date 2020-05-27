# EPMT

Experiment Performance Management Tool a.k.a Workflow DB

This is a tool to collect metadata and performance data about an entire job down to the individual threads in individual processes. This tool uses **papiex** to perform the process monitoring. This tool is targeted at batch or ephemeral jobs, not daemon processes. 

The software contained in this repository was written by Philip Mucci of Minimal Metrics LLC.

## Installation With Release File

The release file includes EPMT, Data Collection Libraries, Notebook and EPMT Workflow GUI. 

For installing with a release file you'll need:

* CentOS 6 or 7
* Release file `EPMT-release-(Version)-(OS).tgz` ex: EPMT-release-3.8.20-centos-7.tgz
* Installer script `epmt-installer`

### Run Install Script

Use the provided epmt-installer script 

$ ./epmt-installer EPMT-release-**version**-**os**.tgz


```
epmt-installer  EPMT-release-3.8.20-centos-7.tgz
 chris@chrisOpti:/tmp/ep-inst$ ls
 chris@chrisOpti:/tmp/ep-inst$ ./epmt-installer EPMT-release-3.8.20-centos-7.tgz 
 Using release: /tmp/ep-inst/EPMT-release-3.8.20-centos-7.tgz
 
 Enter full path to an empty install directory [/tmp/ep-inst/epmt-3.8.20]: 
 Install directory: /tmp/ep-inst/epmt-3.8.20
 Press ENTER to continue, Ctrl-C to abort: 
 Extracting release..
 Installing settings.py and migrations
 Fixing paths in slurm scripts
 EPMT 3.8.20
 
 ***********************************************************************
 Installation successful.
 EPMT 3.8.20 installed in: /tmp/ep-inst/epmt-3.8.20
 
 Please add /tmp/ep-inst/epmt-3.8.20/epmt-install/epmt to PATH:
 
 For Bash:
     export PATH="/tmp/ep-inst/epmt-3.8.20/epmt-install/epmt:$PATH"
 
 Or, for C shell/tcsh:
     setenv PATH "/tmp/ep-inst/epmt-3.8.20/epmt-install/epmt:$PATH"
 
 If you prefer using modules, you can instead do:
     module load /tmp/ep-inst/epmt-3.8.20/modulefiles/epmt
 ***********************************************************************
```

### Add EPMT to path

```text
chris@chrisOpti:/tmp/ep-inst$ export PATH="/tmp/ep-inst/epmt-3.8.20/epmt-install/epmt:$PATH"
# Move away from install directory to test updating path
chris@chrisOpti:/tmp/ep-inst$ cd /tmp/
chris@chrisOpti:/tmp/$ epmt --version
EPMT 3.8.20
```

### Verify installation
Here I add a verbosity switch to get a detailed check output
```text
 $epmt -v check
    INFO: orm.sqlalchemy: sqlalchemy orm selected
    INFO: orm.sqlalchemy: Creating engine with db_params: {'url': 'sqlite:////home/chris/ EPMT_DB.sqlite', 'echo': False}
    INFO: alembic.runtime.migration: Context impl SQLiteImpl.
    INFO: alembic.runtime.migration: Will assume non-transactional DDL.
    INFO: orm.sqlalchemy: database schema up-to-date (version 392efb1132ae)
 settings.db_params = {'url': 'sqlite:////home/chris/EPMT_DB.sqlite', 'echo': False}     Pass
    INFO: epmt_cmds:     ls -l /tmp/ep-inst/epmt-3.8.20/papiex-epmt-install/lib/libpapiex.so>/ dev/null 2>&1
    INFO: epmt_cmds:     ls -l /tmp/ep-inst/epmt-3.8.20/papiex-epmt-install/lib/libmonitor.so>/ dev/null 2>&1
    INFO: epmt_cmds:     ls -l /tmp/ep-inst/epmt-3.8.20/papiex-epmt-install/lib/libpapi.so>/ dev/null 2>&1
    INFO: epmt_cmds:     ls -l /tmp/ep-inst/epmt-3.8.20/papiex-epmt-install/lib/libpfm.so>/dev/ null 2>&1
    INFO: epmt_cmds:     ls -l /tmp/ep-inst/epmt-3.8.20/papiex-epmt-install/bin/ papi_command_line>/dev/null 2>&1
 settings.install_prefix = /tmp/ep-inst/epmt-3.8.20/papiex-epmt-install/ Pass
    INFO: epmt_cmds:     mkdir -p /tmp/epmt/
    INFO: epmt_cmds:     mkdir -p /tmp/epmt/tmp
    INFO: epmt_cmds: created dir /tmp/epmt/tmp
    INFO: epmt_cmds:     ls -lR /tmp/epmt/ >/dev/null
    INFO: epmt_cmds:     rm -rf /tmp/epmt/tmp
 settings.epmt_output_prefix = /tmp/epmt/        Pass
    INFO: epmt_cmds: perf_event_paranoid is 1
 /proc/sys/kernel/perf_event_paranoid =  1       Pass
    INFO: epmt_cmds:     /tmp/ep-inst/epmt-3.8.20/papiex-epmt-install/bin/papi_component_avail  2>&1 | sed -n -e '/Active/,$p' | grep perf_event >/dev/null 2>&1
    INFO: epmt_cmds:     /tmp/ep-inst/epmt-3.8.20/papiex-epmt-install/bin/papi_command_line 2>& 1 PERF_COUNT_SW_CPU_CLOCK| sed -n -e '/PERF_COUNT_SW_CPU_CLOCK\ :/,$p' | grep  PERF_COUNT_SW_CPU_CLOCK > /dev/null 2>&1
 settings.papiex_options = PERF_COUNT_SW_CPU_CLOCK       Pass
 epmt stage functionality        Pass
    INFO: epmt_cmds:     epmt run -a /bin/sleep 1, output to <built-in function dir>
    INFO: epmt_cmds: jobid = 1, dir = /tmp/epmt/chris/1/, file = /tmp/epmt/chris/1/job_metadata
    INFO: epmt_cmds: Forcing epmt_start
    INFO: epmt_cmds: jobid = 1, dir = /tmp/epmt/chris/1/, file = /tmp/epmt/chris/1/job_metadata
    INFO: epmt_cmds: created dir /tmp/epmt/chris/1/
    INFO: epmt_cmds: pickled to /tmp/epmt/chris/1/job_metadata
    INFO: epmt_cmds: Executing(PAPIEX_OUTPUT=/tmp/epmt/chris/1/  PAPIEX_OPTIONS=PERF_COUNT_SW_CPU_CLOCK LD_PRELOAD=/tmp/ep-inst/epmt-3.8.20/ papiex-epmt-install/lib/libpapiex.so:/tmp/ep-inst/epmt-3.8.20/papiex-epmt-install/lib/ libmonitor.so:/tmp/ep-inst/epmt-3.8.20/papiex-epmt-install/lib/libpapi.so:/tmp/ep-inst/ epmt-3.8.20/papiex-epmt-install/lib/libpfm.so:  /bin/sleep 1)
    INFO: epmt_cmds: Exit code 0
    INFO: epmt_cmds: Forcing epmt_stop
    INFO: epmt_cmds: jobid = 1, dir = /tmp/epmt/chris/1/, file = /tmp/epmt/chris/1/job_metadata
    INFO: epmt_cmds: Unpickling from /tmp/epmt/chris/1/job_metadata
    INFO: epmt_cmds: read job start metadata from /tmp/epmt/chris/1/job_metadata
 WARNING: epmtlib: No job name found, defaulting to unknown
    INFO: epmt_cmds: pickled to /tmp/epmt/chris/1/job_metadata
    INFO: epmt_cmds: jobid = 1, dir = /tmp/epmt/chris/1/, file = /tmp/epmt/chris/1/job_metadata
    INFO: epmt_cmds: rmtree /tmp/epmt/chris/1/
 epmt run functionality  Pass
```


---


### Perf Event System Setting

For detailed hardware and software performance metrics to collected by non-privileged users, the following setting must be verified/modified:

```text
 # A value of 3 means the system is totally disabled
 $ cat /proc/sys/kernel/perf_event_paranoid
 3 
 $ # Allow root and non-root users to use the perf subsystem
 # echo 1 > /proc/sys/kernel/perf_event_paranoid
 $ cat /proc/sys/kernel/perf_event_paranoid
 1

```

This isn't necessary unless one would like to collect metrics exposed by [PAPI](http://icl.utk.edu/papi/), [libpfm](http://perfmon2.sourceforge.net/) and the [perfevent](http://web.eece.maine.edu/~vweaver/projects/perf_events/) subsystems. Collecting subsystem data is the premise of EPMT. See [Stack Overflow](https://stackoverflow.com/questions/51911368/what-restriction-is-perf-event-paranoid-1-actually-putting-on-x86-perf) for a discussion of the setting. A setting of 1 is perfectly safe for production systems.

## Modes of EPMT

There are three modes to **EPMT** usage, collection, submission and analysis, and have an increasing number of dependencies:

* **Collection** only requires a minimal Python installation of 2.6.x or higher
* **Submission** requires Python packages for data and database interaction
* **Analysis** requires [Jupyter](https://jupyter.org), an iPython notebook environment, as well as additional python data analysis libraries.

### Configuration
  
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

Immediately after installation, but before configuration of **settings.py** , run the **collection** regression tests using *make check*.

```text
$ make check
make[1]: Entering directory '/build/epmt'
PAPIEX_OUTPUT=/build/epmt  python -m py_compile *.py models/*.py         # Compile everything
PAPIEX_OUTPUT=/build/epmt  ./epmt -h >/dev/null      # help path 1
PAPIEX_OUTPUT=/build/epmt  ./epmt help >/dev/null    # help path 2
PAPIEX_OUTPUT=/build/epmt  ./epmt start           # Generate prolog
.
.
.
job_pl_start            2019-03-06 15:29:35.706748                              
job_pl_submit           2019-03-06 15:29:35.706804                              
job_pl_username         root                                                    
PAPIEX_OUTPUT=/build/epmt  ./epmt -n submit       # Submit
Python 2.7.12
Tests pass! 
```

We can now collect some test data.  

```text
$ ./epmt run -a firefox
$ ls /tmp/epmt/1/
job_metadata  linuxkit-025000000001-papiex-14346-0.csv
```

If this fails, then it's likely the papiex installation is either missing or misconfigured in **settings.py**. The **-a** flag tells **EPMT** to treat this run as an entire **job**. See **README.md** for further details.

### Submission

We can submit our previous job to the default, in-memory, database defined in **settings.py**:

```text
$ ./epmt -v submit /tmp/epmt/1/
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

You are ready to configure a real database.

#### Connecting EPMT to a Database

Using the prebuilt settings files located in the epmt install directory(/opt/minimalmetrics/epmt-(Version)/epmt-install/preset_settings)
```text
$ cd /opt/minimalmetrics/epmt-3.8.20/epmt-install/epmt
$ rm settings.py
$ ln -s ../preset_settings/settings_pg_container_sqlalchemy.py settings.py
$ grep db_params settings.py
db_params = { 'url': 'postgresql://postgres:example@postgres:5432/EPMT', 'echo': False }
```

The database is ready to go.

#### Dropping and Recreating Database 
The drop command will confirm you wish to drop the database.
```
$ epmt drop
This will drop the entire database. This action cannot be reversed. Are you sure (yes/NO): y
WARNING:orm.sqlalchemy:DROPPING ALL DATA AND TABLES!
```
## Analysis and Visualization


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

The notebook command offers paramaters such as host IP for sharing access to the notebook with machines on the local network, notebook token and notebook password
```
./epmt notebook -- --ip 0.0.0.0 --NotebookApp.token='thisisatoken' --NotebookApp.password='hereisa$upersecurepassword'
```

## Troubleshooting

### Error: `version GLIBC_x.xx not found`

The collector library may not have been built for the current environment or the release
OS version does not match the current environment. 

## Appendix

### Docker Images for the running the EPMT command

The image **epmt-command** is the image that contains a working **epmt** install and all it's dependencies. It's mean to be run as a command with arguments via **docker run**. See **README.md** for more details.

### Testing EPMT Collection with Various Python Versions under Docker

One can test **EPMT** on various versions of python with the following make commands. Each will test against a minimal install of Python, without installing any dependencies. 

```text
make check-python-native
make check-python-2.6
make check-python-2.7
make check-python-3
```


