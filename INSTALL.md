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

```
$ ./epmt-installer EPMT-release-3.8.20-centos-7.tgz 
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
$ export PATH="/tmp/ep-inst/epmt-3.8.20/epmt-install/epmt:$PATH"

$ cd /tmp/
$ epmt --version
EPMT 3.8.20
```

### Verify installation

To verify basic configuration the epmt command **check** should be used:

```text
 $ epmt check
settings.db_params = {'url': 'postgresql://postgres:example@172.18.0.2:5432/EPMT', 'echo': False}       Pass
settings.install_prefix = /home/chris/mm/epmt/../papiex-oss/papiex-epmt-install/        Pass
settings.epmt_output_prefix = /tmp/epmt/        Pass
/proc/sys/kernel/perf_event_paranoid =  1       Pass
settings.papiex_options = PERF_COUNT_SW_CPU_CLOCK       Pass
epmt stage functionality        Pass
WARNING: epmtlib: No job name found, defaulting to unknown
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
