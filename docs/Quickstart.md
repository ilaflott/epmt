# EPMT Release Quickstart

## Download
You should have been provided link to the release tar EPMT-2.1.0.tgz 
as well as an installer script (epmt-installer). Download both of
them and place them in a folder.


## Install

### Automatic install using epmt-installer

Just launch the installer and point it to the release tar.

```
$ ./epmt-installer ./EPMT-2.1.0.tgz 

Using release: /home/tushar/src/EPMT/EPMT-2.1.0.tgz

Enter full path to an empty install directory [/home/tushar/src/EPMT/epmt-2.1.0]: 
Install directory: /home/tushar/src/EPMT/epmt-2.1.0
Press ENTER to continue, Ctrl-C to abort: 
Extracting release..
Installing settings.py
EPMT 2.1.0

Installation successful.
EPMT 2.1.0 installed in: /home/tushar/src/EPMT/epmt-2.1.0

Please add /home/tushar/src/EPMT/epmt-2.1.0/epmt-install/epmt to PATH:

For Bash:
export "PATH=/home/tushar/src/EPMT/epmt-2.1.0/epmt-install/epmt:$PATH"

Or, for C shell/tcsh:
setenv PATH "/home/tushar/src/EPMT/epmt-2.1.0/epmt-install/epmt:$PATH"
```

Once the installer finishes successfully, you should follow the printed
instructions and update your shell startup file. Then logout and login
to update your PATH.



### Manual Install

It is recommended that you do the automatic install using
epmt-installer. If you like, you may instead follow the
manual install instructions:

Untar the release tar (EPMT-2.1.0.tgz), you will get three files

 - papiex-epmt-x.y.z.tgz 
 - epmt-x.y.z.tgz        
 - test-epmt-x.y.z.tgz   
 
Then set the environment variables below:

```
EPMT_VERSION=2.1.0
EPMT_PREFIX=/path/to/install
EPMT_DOWNLOAD=/path/to/download
```

Now perform the following steps:

```
mkdir -p $EPMT_PREFIX
cd $EPMT_PREFIX
tar xf $EPMT_DOWNLOAD/epmt-$EPMT_VERSION.tgz
tar xf $EPMT_DOWNLOAD/papiex-epmt-$EPMT_VERSION.tgz
tar xf $EPMT_DOWNLOAD/test-epmt-$EPMT_VERSION.tgz
cp epmt-install/preset_settings/settings_sqlite_localfile_sqlalchemy.py epmt-install/epmt/settings.py
$EPMT_PREFIX/epmt-install/epmt/epmt -V
```

***IMPORTANT***

***The below instructions uses a SQLite database with an on-disk data store, which is scalable only to a few thousand jobs. You may use `settings_pg_localhost_sqlalchemy.py` to set up a connection to a PostGres database instance, which is the recommended configuration. `settings_sqlite_inmem_sqlalchemy.py` is also available for ephemeral testing.***

Modify install, output and stage paths, and possibly the database connection string, in your copied `settings.py` file.

`vi $EPMT_PREFIX/epmt-install/epmt/settings.py`

```
install_prefix = <value of EPMT_PREFIX>/papiex-epmt-install/
epmt_output_prefix = "/tmp/epmt/"
stage_command = "mv"
stage_command_dest = "./"
```

Now check everything works as expected.

```
$EPMT_PREFIX/epmt-install/epmt/epmt -V
$EPMT_PREFIX/epmt-install/epmt/epmt check
```

If everything looks good, add `epmt` to your path. For ***Bash***:
```
export PATH=$EPMT_PREFIX/epmt-install/epmt:$PATH
```
or for ***C shell***:
```
setenv PATH $EPMT_PREFIX/epmt-install/epmt:$PATH
```
## Usage

### Manual Usage

See examples in the `$EPMT_PREFIX/epmt-install/examples/` directory.


```
$ cat epmt-example.csh
#!/bin/tcsh

setenv SHELL /bin/tcsh
epmt start             # Generate prolog
eval `epmt source`     # Setup environment
/bin/sleep 1 >& /dev/null   # Workload
epmt_uninstrument      # End Workload
epmt stop              # Wrap up job stats
set f=`epmt stage`     # Move to medium term storage ($PWD)
epmt submit $f         # Submit to DB, should do elsewhere

$ sbatch epmt-example.csh
```

***IMPORTANT***

***Submit should not be performed as part of the job as currently this can take some time***

### Automatic instrumentation using SLURM

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

## Testing (Optional)

### Run integration tests
```
$EPMT_PREFIX/test/integration/run_integration 
 ✓ epmt version
 ✓ epmt submit
 - epmt_concat -h (skipped)
 - epmt_concat with valid input dir (skipped)
 - epmt_concat with valid input files (skipped)
 - epmt_concat with non-existent directory (skipped)
 - epmt_concat with non-existent files (skipped)
 - epmt_concat with corrupted csv (skipped)
 ✓ no daemon running
 ✓ start epmt daemon
 ✓ stop epmt daemon

11 tests, 0 failures, 6 skipped
```

### Run unit tests
```
$ epmt unittest
```

