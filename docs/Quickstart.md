# EPMT Release Quickstart

## Download
You should have been provided links to three compressed tar files, consisting of *papiex*, *epmt* and *tests*.

 - papiex-epmt-x.y.z.tgz 
 - epmt-x.y.z.tgz        
 - test-epmt-x.y.z.tgz   
 
Download each of the above and decide on locations for the installation. Then set the environment variables below to those locations as well as the version.

```
EPMT_VERSION=2.1.0
EPMT_INSTALL=/path/to/install
EPMT_DOWNLOAD=/path/to/download
```

## Installation

---
***IMPORTANT***

The below instructions uses a SqlLite database with an on-disk data store, which is scalable only to a few thousand jobs. You may use `settings_pg_localhost_sqlalchemy.py` to set up a connection to a PostGres database instance, which is the recommended configuration. `settings_sqlite_inmem_sqlalchemy.py` is also available for ephemeral testing.

---

Now perform the installation:

```
mkdir -p $EPMT_INSTALL
cd $EPMT_INSTALL
tar xf $EPMT_DOWNLOAD/epmt-$EPMT_VERSION.tgz
tar xf $EPMT_DOWNLOAD/papiex-epmt-$EPMT_VERSION.tgz
tar xf $EPMT_DOWNLOAD/test-epmt-$EPMT_VERSION.tgz
cp epmt-install/preset_settings/settings_sqlite_localfile_sqlalchemy.py epmt-install/epmt/settings.py
$EPMT_INSTALL/epmt-install/epmt/epmt -V
```


Now modify install, output and stage paths, and possibly the database connection string, in your copied `settings.py` file.

`vi $EPMT_INSTALL/epmt-install/epmt/settings.py`

```
install_prefix = <value of EPMT_INSTALL>/papiex-epmt-install/
epmt_output_prefix = "/tmp/epmt/"
stage_command = "mv"
stage_command_dest = "./"
```

Now check everything works as expected.

```
$EPMT_INSTALL/epmt-install/epmt/epmt -V
$EPMT_INSTALL/epmt-install/epmt/epmt check
```

If everything looks good, add `epmt` to your path. For ***Bash***:
```
export PATH=$EPMT_INSTALL/epmt-install/epmt:$PATH
```
or for ***csh***:
```
setenv PATH $EPMT_INSTALL/epmt-install/epmt:$PATH
```
## Usage

### Manual Usage

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
epmt submit $f         # Submit to DB

$ sbatch epmt-example.csh
```

### Automatic instrumentation using SLURM


## Testing (Optional)

### Run integration tests
```
$EPMT_INSTALL/test/integration/run_integration 
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

