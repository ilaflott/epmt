#!/usr/bin/env python
from __future__ import print_function
from datetime import datetime
from os import environ, makedirs, mkdir, path, getpid, getsid, getcwd, chdir, unlink, listdir
from socket import gethostname
from subprocess import call as forkexecwait
from random import randint
from imp import find_module
from glob import glob
from sys import stdout, stderr
from json import dumps, loads
import errno

from shutil import rmtree
import fnmatch
import pickle
from logging import getLogger, basicConfig, DEBUG, INFO, WARNING, ERROR
logger = getLogger(__name__)  # you can use other name
import epmt_settings as settings

from epmtlib import get_username, epmt_logging_init, init_settings, conv_dict_byte2str, cmd_exists, run_shell_cmd, safe_rm, timing, dict_filter, check_fix_metadata

def find_diffs_in_envs(start_env,stop_env):
    env = {}
    for e in start_env.keys():
        if e in stop_env.keys():
            if start_env[e] == stop_env[e]:
                logger.debug("Found "+e)
            else:
                logger.debug("Different "+e)
                env[e] = stop_env[e]
        else:
            logger.debug("Deleted "+e)
            env[e] = start_env[e]
    for e in stop_env.keys():
        if e not in start_env.keys():
            logger.debug("Added "+e)
            env[e] = stop_env[e]
    return env


def dump_config(outf):
    print("\nsettings.py (affected by the below env. vars):", file=outf)
#    book = {}
    for key, value in sorted(settings.__dict__.items()):
        if not (key.startswith('__') or key.startswith('_')):
            print("%-24s%-56s" % (key,str(value)), file=outf)
    print("\nenvironment variables (overrides settings.py):", file=outf)
    for v in [ "PAPIEX_OSS_PATH", "PAPIEX_OUTPUT", "EPMT_DB_PROVIDER", "EPMT_DB_USER", "EPMT_DB_PASSWORD", "EPMT_DB_HOST", "EPMT_DB_DBNAME", "EPMT_DB_FILENAME" ]:
#                "provider", "user", "password", "host", "dbname", "filename" ]:
# "PAPIEX_OPTIONS","PAPIEX_DEBUG","PAPI_DEBUG","MONITOR_DEBUG","LIBPFM_DEBUG"
#              ]:
        if v in environ:
            print("%-24s%-56s" % (v,environ[v]), file=outf)

def read_job_metadata_direct(file):
    try:
        data = pickle.load(file)
    except UnicodeDecodeError:
        # python3 gives problems unpickling stuff pickled using python2
        logger.debug("doing special unpickling for job metadata pickled using python2")
        data = conv_dict_byte2str(pickle.load(file, encoding='bytes'))
    except Exception as e:
        logger.error("Error unpickling job metadata file: {}".format(e))
        raise
    logger.debug("Unpickled ")
    return data

def read_job_metadata(jobdatafile):
    logger.info("Unpickling from "+jobdatafile)
    try:
        with open(jobdatafile,'rb') as file:
            return read_job_metadata_direct(file)
    except IOError as i:
        logger.error("Job metadata missing, possibly didn't start? %s", str(i))
    return False

def write_job_epilog(jobdatafile,metadata):
    with open(jobdatafile,'w+b') as file:
        pickle.dump(metadata,file)
        logger.debug("Pickled to "+jobdatafile)
        return True
    return False

#
#
#
#db.bind(**settings.db_params)
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def PrintFail():
    print("\t" + bcolors.FAIL + "Fail" + bcolors.ENDC)
def PrintPass():
    print("\t" + bcolors.OKBLUE + "Pass" + bcolors.ENDC)
def PrintWarning():
    print("\t" + bcolors.WARNING + "Pass" + bcolors.ENDC)

def verify_install_prefix():
    install_prefix = settings.install_prefix
    print("settings.install_prefix =",install_prefix, end='')
    retval = True
# Check for bad stuff and shortcut
    if "*" in install_prefix or "?" in install_prefix:
        logger.error("Found wildcards in install_prefix: {}".format(install_prefix))
        PrintFail()
        return False
    for e in [ "lib/libpapiex.so","lib/libmonitor.so",
               "lib/libpapi.so","lib/libpfm.so","bin/papi_command_line" ]:
        cmd = "ls -l "+install_prefix+e+">/dev/null 2>&1"
        logger.info("\t"+cmd)
        return_code = forkexecwait(cmd, shell=True)
        if return_code != 0:
            logger.error("%s failed",cmd)
            retval = False

    if retval == True:
        PrintPass()
    else:
        PrintFail()
    return retval
    
def verify_epmt_output_prefix():
    opf = settings.epmt_output_prefix
    print("settings.epmt_output_prefix =",opf, end='')
    retval = True
# Check for bad stuff and shortcut
    if "*" in opf or "?" in opf:
        logger.error("Found wildcards in value: %s",opf)
        PrintFail()
        return False
# Print and create dir
    def testdir(str2):
        logger.info("\tmkdir -p "+str2)
        return(create_job_dir(str2))
# Test create (or if it exists)
    if testdir(opf) == False:
        retval = False
# Test make a subdir
    if testdir(opf+"tmp") == False:
        retval = False
# Test to make sure we can access it
    cmd = "ls -lR "+opf+" >/dev/null"    
    logger.info("\t"+cmd)
    return_code = forkexecwait(cmd, shell=True)
    if return_code != 0:
        retval = False
# Remove the created tmp dir
    cmd = "rm -rf "+opf+"tmp"
    logger.info("\t"+cmd)
    return_code = forkexecwait(cmd, shell=True)
    if return_code != 0:
        retval = False
# Cleanup
    if retval == True:
        PrintPass()
    else:
        PrintFail()
    return retval


def verify_papiex_options():
    str = settings.papiex_options
    print("settings.papiex_options =",str, end='')
    retval = True
# Check for any components
    cmd = settings.install_prefix+"bin/papi_component_avail 2>&1 "+"| sed -n -e '/Active/,$p' | grep perf_event >/dev/null 2>&1"
    logger.info("\t"+cmd)
    return_code = forkexecwait(cmd, shell=True)
    if return_code != 0:
        logger.error("%s failed",cmd)
        retval = False
# Now check events
    eventlist = str.split(',')
    for e in eventlist:
        cmd = settings.install_prefix+"bin/papi_command_line 2>&1 "+e+"| sed -n -e '/PERF_COUNT_SW_CPU_CLOCK\ :/,$p' | grep PERF_COUNT_SW_CPU_CLOCK > /dev/null 2>&1"
        logger.info("\t"+cmd)
        return_code = forkexecwait(cmd, shell=True)
        if return_code != 0:
            logger.error("%s failed",cmd)
            retval = False
# End
    if retval == True:
        PrintPass()
    else:
        PrintFail()
    return retval

def verify_db_params():
    print("settings.db_params =",str(settings.db_params), end='')
    try:
        from orm import setup_db
        if setup_db(settings) == False:
            PrintFail()
            return False
        else:
            PrintPass()
            return True
    except ImportError:
        logger.error("pony module not installed, see INSTALL.md");
        PrintFail()
        return False
    
def verify_perf():
    f="/proc/sys/kernel/perf_event_paranoid"
    print(f,end='')
    try:
        with open(f, 'r') as content_file:
            value = int(content_file.read())
            print(" = ",value, end='')
            if value > 1:
                logger.error("bad %s value of %d, should be 1 or less to allow cpu events",f,value)
                PrintFail()
                return False
            logger.info("perf_event_paranoid is %d",value)
            PrintPass()
            return True
    except Exception as e:
        print(str(e), file=stderr)
        PrintFail()
    return False

def verify_stage_command():
    print("epmt stage functionality", end='')
    stage_cmd = settings.stage_command
    if not(cmd_exists(stage_cmd)):
        PrintFail()
        return False
    dest = settings.stage_command_dest
    if (not dest) or (not path.isdir(dest)):
        PrintFail()
        return False
    tmp = environ.get('TMPDIR', '/tmp')
    tmpfile = 'test_stage_cmd'
    inp = '/{0}/{1}'.format(tmp, tmpfile)
    target = '{0}/{1}'.format(dest, tmpfile)
    try:
        safe_rm(target)
        open(inp, 'a').close()
        run_shell_cmd(stage_cmd, inp, dest)
        if not path.exists(target):
            raise("could not create output in {0}".format(dest))
    except Exception as e:
        print(str(e), file=stderr)
        PrintFail()
        return False
    finally:
        safe_rm(inp)
        safe_rm(target)
    PrintPass()
    return True

def verify_papiex():
    print("epmt run functionality", end='')
    logger.info("\tepmt run -a /bin/sleep 1, output to %s",dir)
    retval = epmt_run(["/bin/sleep","1"],wrapit=True)
    if retval != 0:
        retval = False
    else:
        retval = True
        global_jobid,global_datadir,global_metadatafile = setup_vars()
        files = glob(global_datadir+settings.input_pattern)
        if len(files) != 1:
            logger.error("%s matched %d papiex CSV output files instead of 1",global_datadir+settings.input_pattern,len(files))
            retval = False
    if retval == True:
        files = glob(global_datadir+"job_metadata")
        if len(files) != 1:
            logger.error("%s matched %d job_metadata files instead of 1",global_datadir+"job_metadata",len(files))
            retval = False

    if retval == True:
        logger.info("rmtree %s",global_datadir) 
        rmtree(global_datadir)
        PrintPass()
    else:
        PrintFail()
    return retval

def epmt_check():
    retval = True
    if verify_db_params() == False:
        retval = False
    if verify_install_prefix() == False:
        retval = False
    if verify_epmt_output_prefix() == False:
        retval = False
    if verify_perf() == False:
        retval = False
    if verify_papiex_options() == False:
        retval = False
    if verify_stage_command() == False:
        retval = False
    if verify_papiex() == False:
        retval = False
    return retval

#
# These two functions should match _check_and_create_metadata!
#

def create_start_job_metadata(jobid, submit_ts, from_batch=[]):
    # from tzlocal import get_localzone
    # use timezone info if available, otherwise use naive datetime objects
    try:
        # ts=datetime.now(tz=get_localzone())
        ts=datetime.now().astimezone()
    except:
        ts=datetime.now()
    metadata = {}
    start_env=dict_filter(environ, vars(settings).get('env_blacklist',None))
#   print env
    metadata['job_pl_id'] = jobid
#   metadata['job_pl_hostname'] = gethostname()
    if submit_ts == False:
        metadata['job_pl_submit_ts'] = ts
    else:
        metadata['job_pl_submit_ts'] = submit_ts
    metadata['job_pl_start_ts'] = ts
    metadata['job_pl_env'] = start_env
    metadata['job_pl_username'] = get_username()
    return metadata

def merge_stop_job_metadata(metadata, exitcode, reason, from_batch=[]):
    # from tzlocal import get_localzone
    # use timezone info if available, otherwise use naive datetime objects
    try:
        # ts=datetime.now(tz=get_localzone())
        ts=datetime.now().astimezone()
    except:
        ts=datetime.now()
    stop_env=dict_filter(environ, vars(settings).get('env_blacklist',None))
    metadata['job_el_stop_ts'] = ts
    metadata['job_el_exitcode'] = exitcode
    metadata['job_el_reason'] = reason
    metadata['job_el_env'] = stop_env
    return metadata

def create_job_dir(dir):
    try:
        makedirs(dir) 
        logger.info("created dir %s",dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            logger.error("dir %s: %s",dir,e)
            return False
        logger.debug("dir exists %s",dir)
    return dir
    
def write_job_metadata(jobdatafile,data):
    with open(jobdatafile,'w+b') as file:
        pickle.dump(data,file)
        logger.info("pickled to %s",jobdatafile);
        logger.debug("Data %s",data)
        return True
    return False
    # collect env

def setup_vars():
    """
    If you call setup vars, it's because you need the jobid,csvdir,metadatafile triple
    that is extracted from the environment. If this isn't found, you will get an error.
    """
    def get_jobid():
        for e in settings.jobid_env_list:
            jid = environ.get(e)
            if jid and len(jid) > 0:
                return jid
        logger.error("No key of %s was found in environment",settings.jobid_env_list)
        return False

    jobid = get_jobid()
    if not jobid:
        return False,False,False

    dir = settings.epmt_output_prefix + get_username() + "/" + jobid + "/"
    file = dir + "job_metadata"
    logger.info("jobid = %s, dir = %s, file = %s",jobid,dir,file)
    return jobid,dir,file

def epmt_start_job(other=[]):
    global_jobid,global_datadir,global_metadatafile = setup_vars()
    if not (global_jobid and global_datadir and global_metadatafile):
        return False
        
    metadata = create_start_job_metadata(global_jobid,False,other)
    if create_job_dir(global_datadir) is False:
        return False
    if path.exists(global_metadatafile):
        logger.error("%s already exists!",global_metadatafile)
        return False
    retval = write_job_metadata(global_metadatafile,metadata)
    return retval

def epmt_stop_job(other=[]):
    global_jobid,global_datadir,global_metadatafile = setup_vars()
    if not (global_jobid and global_datadir and global_metadatafile):
        return False

    start_metadata = read_job_metadata(global_metadatafile)
    if not start_metadata:
        return False
    logger.info("read job start metadata from %s",global_metadatafile);
    if "job_el_stop_ts" in start_metadata:
        logger.error("%s is already complete!",global_metadatafile)
        return False
    metadata = merge_stop_job_metadata(start_metadata,0,"none",other)
    checked_metadata = check_fix_metadata(metadata)
    if not checked_metadata:
        logger.error('Metadata check failed. Writing raw metadata for post-mortem analysis.')
        checked_metadata = metadata
    retval = write_job_metadata(global_metadatafile,checked_metadata)
    return retval

def epmt_dump_metadata(filelist):
    if not filelist:
        global_jobid,global_datadir,global_metadatafile = setup_vars()
        if not (global_jobid and global_datadir and global_metadatafile):
            return False
        infile = [global_metadatafile]
    else:
        infile = filelist
    if not infile or len(infile) < 1:
        logger.error("Could not identify your job id")
        return False

    for file in filelist:
        if not path.exists(file):
            logger.error("%s does not exist!",file)
            return False

        err,tar = compressed_tar(file)
        if tar:
            try:
                info = tar.getmember("./job_metadata")
            except KeyError:
                logger.error('ERROR: Did not find %s in tar archive' % "job_metadata")
                return False
            else:
                logger.info('%s is %d bytes in archive' % (info.name, info.size))
                f = tar.extractfile(info)
                metadata = read_job_metadata_direct(f)
        else:
            metadata = read_job_metadata(file)
            print(metadata)

        if not metadata:
            return False
        for d in sorted(metadata.keys()):
            print("%-24s%-56s" % (d,str(metadata[d])))
    return True

def epmt_source(slurm_prolog=False, papiex_debug=False, monitor_debug=False, run_cmd=False):
    """

    epmt_source - produces shell variables that enable transparent instrumentation

    run_cmd: - used when instrumentation is done on the command line by the epmt run command


    """

    global_jobid,global_datadir,global_metadatafile = setup_vars()
    if not (global_jobid and global_datadir and global_metadatafile):
        return False

    def detect_csh():
        for v in [ environ.get("_"), environ.get("SHELL") ]:
            if (v and v.endswith("csh")):
                logger.debug("Detected CSH - Please read https://www-uxsup.csx.cam.ac.uk/misc/csh.html")
                return True
        return False
    
    sh_set_var=""
    equals="="
    cmd_sep=";\n"
    cmd=""
    undercsh=False
    
    if slurm_prolog:
        sh_set_var="export "
        cmd_sep="\n"
    else:
        undercsh=detect_csh()        

    if run_cmd: 
        undercsh = False # All commands under run are started under Bash in Python
        cmd_sep=" "
    if undercsh:
        aliasing = True
        sh_set_var="set "

    def add_var(cmd,str):
        cmd += sh_set_var
        cmd += str
        cmd += cmd_sep
        return cmd

    cmd = ""
    if monitor_debug: cmd = add_var(cmd,"MONITOR_DEBUG"+equals+"TRUE")
    if papiex_debug: cmd = add_var(cmd,"PAPIEX_DEBUG"+equals+"TRUE")
    cmd = add_var(cmd,"PAPIEX_OUTPUT"+equals+global_datadir) 
    cmd = add_var(cmd,"PAPIEX_OPTIONS"+equals+settings.papiex_options)
    oldp = environ.get("LD_PRELOAD")
    if oldp: cmd = add_var(cmd,"OLD_LD_PRELOAD"+equals+oldp)
    cmd = add_var(cmd,"LD_PRELOAD"+equals+
                  settings.install_prefix+"lib/libpapiex.so:"+
                  settings.install_prefix+"lib/libpapi.so:"+
                  settings.install_prefix+"lib/libpfm.so:"+
                  settings.install_prefix+"lib/libmonitor.so"+((":"+oldp) if oldp else ""))
#
# Use export -n which keeps the variable but prevents it from being exported
#
    if undercsh:
        tmp = "setenv PAPIEX_OPTIONS $PAPIEX_OPTIONS; setenv LD_PRELOAD $LD_PRELOAD;"
        tmp += "setenv PAPIEX_OUTPUT $PAPIEX_OUTPUT;"
        if monitor_debug: tmp += "setenv MONITOR_DEBUG $MONITOR_DEBUG;"
        if papiex_debug: tmp += "setenv PAPIEX_DEBUG $PAPIEX_DEBUG;" 
        cmd += "alias epmt_instrument '"+tmp+"';\n"
        cmd += "alias epmt_uninstrument 'unsetenv MONITOR_DEBUG PAPIEX_OUTPUT PAPIEX_DEBUG PAPIEX_OPTIONS"
        if not oldp:
            cmd += " LD_PRELOAD';"
        else:
            cmd += "';\nsetenv LD_PRELOAD=$OLD_LD_PRELOAD;"
        # CSH won't let an alias used in eval be used in the same eval, so we repeat this
        cmd +="\n"+tmp+"\n"
    elif not run_cmd and not slurm_prolog:
        cmd += "epmt_instrument ()\n{\nexport MONITOR_DEBUG PAPIEX_OUTPUT PAPIEX_DEBUG PAPIEX_OPTIONS LD_PRELOAD;\n};\n"
        cmd += "epmt_uninstrument ()\n{\nexport -n MONITOR_DEBUG PAPIEX_OUTPUT PAPIEX_DEBUG PAPIEX_OPTIONS"
        if not oldp:
            cmd += " LD_PRELOAD;\n"
        else:
            cmd += "\nexport LD_PRELOAD=$OLD_LD_PRELOAD;\n"
        cmd +="};\nepmt_instrument;\n"

    return cmd

def epmt_run(cmdline, wrapit=False, dry_run=False, debug=False):
    # logger.debug("epmt_run(%s, %s, %s, %s, %s)", cmdline, str(wrapit), str(dry_run), str(debug))

    if not cmdline:
        logger.error("No command given")
        return(1)

    cmd = epmt_source(papiex_debug=debug, monitor_debug=debug, run_cmd=True)
    if not cmd:
        return 1 
    cmd += " "+" ".join(cmdline)

    if wrapit:
        logger.info("Forcing epmt_start")
        if dry_run:
            print("epmt start")
        else:
            if not epmt_start_job():
                return 1

    logger.info("Executing(%s)",cmd)
    if not dry_run:
        return_code = forkexecwait(cmd, shell=True)
        logger.info("Exit code %d",return_code)
    else:
        print(cmd)
        return_code = 0

    if wrapit:
        logger.info("Forcing epmt_stop")
        if dry_run:
            print("epmt stop")
        else:
            epmt_stop_job()
    return return_code

def get_filedict(dirname,pattern,tar=False):
    logger.debug("get_filedict(%s,%s,tar=%s)",dirname,pattern,str(tar))
    # Now get all the files in the dir
    if tar:
        files = fnmatch.filter(tar.getnames(), pattern)
    else:
        files = glob(dirname+pattern)

    if not files:
        logger.info("%s matched no files",pattern)
        return {}

    logger.info("%d files to submit",len(files))
    if (len(files) > 30):
        logger.debug("Skipping printing files, too many")
    else:
        logger.debug("%s",files)

    # Build a hash of hosts and their data files
    filedict={}
    dumperr = False
    for f in files:
        t = path.basename(f)
        ts = t.split("papiex")
        if len(ts) == 2:
            if len(ts[0]) == 0:
                host = "unknown"
                dumperr = True
            else:
                host = ts[0]
        else:
            logger.warn("Split failed of %s, only %d parts",t,len(ts))
            continue
# Byproduct of collation
        host = host.replace('-collated-','')
        if filedict.get(host):
            filedict[host].append(f)
        else:
            filedict[host] = [ f ]
    if dumperr:
        logger.warn("Host not found in name split, using unknown host")

    return filedict

def epmt_submit(dirs, dry_run=True, drop=False, keep_going=True, ncpus = 1):
    logger.debug("epmt_submit(%s,dry_run=%s,drop=%s,keep_going=%s)",dirs,dry_run,drop,keep_going)
    if not dirs:
        global_jobid,global_datadir,global_metadatafile = setup_vars()
        if not (global_jobid and global_datadir and global_metadatafile):
            return False
        dirs  = [global_datadir]
    if not dirs or len(dirs) < 1:
        logger.error("Could not identify your job id")
        return False
    if dry_run and drop:
        logger.error("You can't drop tables and do a dry run")
        return(False)
    if (ncpus > 1) and (settings.orm != 'sqlalchemy'):
        logger.error('Parallel submit is only supported for SQLAlchemy at present')
        return False
    if drop and (ncpus > 1):
        # FIX:
        # when we do drop tables we end up calling setup_db
        # However, this initializes certain variables and later 
        # when a parallel submit happens setup_db is skipped in the
        # spawned processes. This means SQLA Session isn't initialized
        # with the newly created tables in any of the processes except the
        # master. In short we are unable to support the --drop option
        # when using multiple processes. This should be fixable.
        logger.error('At present we do not support dropping tables in a parallel submit mode. Please use either --drop or --num-cpus')
        return(False)

    if drop:
        from orm import orm_drop_db, setup_db
        setup_db(settings)
        orm_drop_db()

    import multiprocessing

    def submit_fn(tid, work_list, ret_dict):
        from os import getpid
        logger.debug('Worker %d, PID %d', tid, getpid())
        retval = {}
        for f in work_list:
            r = submit_to_db(f,settings.input_pattern,dry_run=dry_run)
            retval[f] = r
            if r[0] is False and not keep_going:
                break
        ret_dict[tid] = dumps(retval)
        return
    # we shouldn't use more processors than the number of discrete
    # work items. We don't currently split the work within a directory.
    # If we a directory is passed we assume it's a single work item.
    # TODO: Get a full files list from all the directories passed and
    # then split the list of files for a better distribution and more
    # optimal parallelization.
    nprocs = min(ncpus, len(dirs))
    num_cores = multiprocessing.cpu_count()
    logger.info('You are running on a machine with %d cores', num_cores)
    logger.info('Found %d items to submit', len(dirs))
    if nprocs > num_cores:
        logger.warning('You have requested to use (%d), which is more than the available cpus (%d)', ncpus, num_cores)
    import time
    worker_id = 0
    start_ts = time.time()
    if nprocs == 1:
        return_dict = {}
        submit_fn(worker_id, dirs, return_dict)
    else:
        logger.info('Using %d worker processes', nprocs)
        from numpy import array_split
        procs = []
        manager = multiprocessing.Manager()
        return_dict = manager.dict()
        for work in array_split(dirs, nprocs):
            logger.debug('Worker %d will work on %s', worker_id, str(work))
            process = multiprocessing.Process(target = submit_fn, args=(worker_id, work, return_dict))
            procs.append(process)
            worker_id += 1
        for p in procs:
            p.start()
        for p in procs:
            p.join()
    fini_ts = time.time()
    r = { k: loads(return_dict[k]) for k, v in return_dict.items() }
    total_procs = 0
    jobs_imported = []
    logger.info('**** Import Summary ****')
    for v in r.values():
        for (f, res) in v.items():
            if res[0] is False:
                logger.error('Error in importing: %s: %s', f, res[1])
            elif res[0] is None:
                logger.warning('%s: %s', res[1], f)
            else:
                (jobid, process_count) = res[-1]
                jobs_imported.append(jobid)
                total_procs += process_count
    logger.info('Imported %d jobs (%d processes) in %2.2f sec at %2.2f procs/sec, %d workers', len(jobs_imported), total_procs, (fini_ts - start_ts), total_procs/(fini_ts - start_ts), nprocs)
    return(r if jobs_imported else False)

def compressed_tar(input):
    tar = None
    flags = None
    if (input.endswith("tar.gz") or input.endswith("tgz")):
        flags = "r:gz"
    elif (input.endswith("tar")):
        flags = "r:"
    else:
        return False,None
    
    import tarfile
    try:
        tar = tarfile.open(input, flags)
    except Exception as e:
        logger.error('error in processing compressed tar: ' + str(e))
        return True,None
    
    return False,tar
    
# Compute differences in environment if detected
# Merge start and stop environments
#    total_env = start_env.copy()
#    total_env.update(stop_env)
# Check for Experiment related variables
#    metadata = check_and_add_workflowdb_envvars(metadata,total_env)

def submit_to_db(input, pattern, dry_run=True):
    logger.info("submit_to_db(%s,%s,dry_run=%s)",input,pattern,str(dry_run))

    err,tar = compressed_tar(input)
    if err:
        return (False, 'Error processing compressed tar')
#    None
#    if (input.endswith("tar.gz") or input.endswith("tgz")):
#        import tarfile
#        tar = tarfile.open(input, "r:gz")
#    elif (input.endswith("tar")):
#        import tarfile
#        tar = tarfile.open(input, "r:")
    if not tar and not input.endswith("/"):
        logger.warning("missing trailing / on submit dirname %s",input);
        input += "/"

    if tar:
#        for member in tar.getmembers():
        try:
            info = tar.getmember("./job_metadata")
        except KeyError:
            logger.error('ERROR: Did not find %s in tar archive' % "job_metadata")
            return (False, 'Did not find metadata in tar archive')
        else:
            logger.info('%s is %d bytes in archive' % (info.name, info.size))
            f = tar.extractfile(info)
            metadata = read_job_metadata_direct(f)
            filedict = get_filedict(None,settings.input_pattern,tar)
    else:
        metadata = read_job_metadata(input+"job_metadata")
        filedict = get_filedict(input,settings.input_pattern)

    if not metadata:
        return (False, 'Did not find valid metadata')

    logger.info("%d hosts found: %s",len(filedict.keys()),filedict.keys())
    for h in filedict.keys():
        logger.info("host %s: %d files to import",h,len(filedict[h]))

# Do as much as we can before bailing
    if dry_run:
#        check_workflowdb_dict(metadata,pfx="exp_")
        logger.info("Dry run finished, skipping DB work")
        return (True, 'Dry run finished, skipping DB work')

# Now we touch the Database
    from orm import setup_db
    if setup_db(settings,False) == False:
        return (False, 'Error in DB setup')
    from epmt_job import ETL_job_dict
    r = ETL_job_dict(metadata,filedict,settings,tarfile=tar)
    # if not r[0]:
    return r
    # (j, process_count) = r[-1]
    # logger.info("Committed job %s to database: %s",j.jobid,j)
    # return (j.jobid, process_count)


def stage_job(dir,collate=True,compress_and_tar=True):
    logger.debug("stage_job(%s,collate=%s,compress_and_tar=%s)",dir,str(collate),str(compress_and_tar))
    if not dir or len(dir) < 1:
        return False
    if settings.stage_command and len(settings.stage_command) and settings.stage_command_dest and len(settings.stage_command_dest):
        try:
            l=listdir(dir)
            if not l:
                logger.error(dir + "is empty")
                return False
        except Exception as e:
            logger.error(str(e))
            return False

        if collate:
            from epmt_concat import csvjoiner
            logger.debug("csvjoiner(%s)",dir)
            status, collated_file = csvjoiner(dir,debug=0)
            if status == False:
                return False
            if status == True and collated_file and len(collated_file) > 0:
                logger.info("Collated file is %s",collated_file)
                newdir = path.dirname(dir)+".collated"
                cmd = "mkdir "+newdir
                logger.debug(cmd)
                return_code = forkexecwait(cmd, shell=True)
                if return_code != 0:
                    return False
                cmd = "cp -p "+dir+"job_metadata "+newdir
                logger.debug(cmd)
                return_code = forkexecwait(cmd, shell=True)
                if return_code != 0:
                    return False
                cmd = "mv "+collated_file+" "+newdir
                logger.debug(cmd)
                return_code = forkexecwait(cmd, shell=True)
                if return_code != 0:
                    return False
                cmd = "mv "+path.dirname(dir)+" "+path.dirname(dir)+".original" 
                logger.debug(cmd)
                return_code = forkexecwait(cmd, shell=True)
                if return_code != 0:
                    return False
                cmd = "mv "+path.dirname(dir)+".collated "+path.dirname(dir)
                logger.debug(cmd)
                return_code = forkexecwait(cmd, shell=True)
                if return_code != 0:
                    return False
                cmd = "rm -rf "+path.dirname(dir)+".original"
                logger.debug(cmd)
                return_code = forkexecwait(cmd, shell=True)
                if return_code != 0:
                    return False

        filetostage = path.dirname(dir)
        if compress_and_tar:
            cmd = "tar -C "+dir+" -cz -f "+path.dirname(dir)+".tgz ."
            logger.debug(cmd)
            return_code = forkexecwait(cmd, shell=True)
            if return_code != 0:
                return False
            filetostage += ".tgz "

        cmd = settings.stage_command + " " + filetostage + " " + settings.stage_command_dest
        logger.debug(cmd)
        return_code = forkexecwait(cmd, shell=True)
        if return_code != 0:
            return False

# Collation does it's own cleanup
        if not collated_file or len(collated_file) == 0:
            cmd = "rm -rf "+dir
            logger.debug(cmd)
            return_code = forkexecwait(cmd, shell=True)
            if return_code != 0:
                return False
        print(settings.stage_command_dest+path.basename(filetostage))
    return True

def epmt_stage(dirs, keep_going=True):
    if not dirs:
        global_jobid,global_datadir,global_metadatafile = setup_vars()
        if not (global_jobid and global_datadir and global_metadatafile):
            return False
        dirs  = [global_datadir]

    logger.debug("epmt_stage(%s)",dirs)
    r = True
    for dir in dirs:
        if not dir.endswith("/"):
            logger.warning("missing trailing / on %s",dir)
            dir += "/"
        jobid = path.basename(path.dirname(dir))
        file = dir + "job_metadata"
        r = stage_job(dir)
        if r is False and not keep_going:
            return False
    return r

def epmt_dbsize(findwhat=['database','table','index','tablespace'], usejson=False, usebytes=False):
    from orm import get_db_size
# Absolutely all argument checking should go here, specifically the findwhat stuff
    return(get_db_size(findwhat,usejson,usebytes))


def epmt_entrypoint(args):

    # I hate this sequence.

    if args.verbose == None:
        args.verbose = 0
    logger = getLogger(__name__)  # you can use other name
    epmt_logging_init(args.verbose, check=False)
    init_settings(settings)
    if not args.verbose:
        epmt_logging_init(settings.verbose, check=True)


    # Here it's up to each command to validate what it is looking for
    # and error out appropriately
    if args.command == 'shell':
        from code import interact
        interact(local=locals())
        return 0
    if args.command == 'gui':
        from ui import init_app, app
        init_app()
        app.run_server(debug=False, host='0.0.0.0')
        return 0
    if args.command == 'unittest':
        import unittest
        from importlib import import_module
        script_dir = path.dirname(path.realpath(__file__))
        logger.info("Changing directory to: {}".format(script_dir))
        chdir(script_dir)
        TEST_MODULES = ['test.test_lib','test.test_settings','test.test_anysh','test.test_submit','test.test_cmds','test.test_query','test.test_outliers','test.test_db_schema' ]
        for m in TEST_MODULES:
            mod = import_module(m)
            suite = unittest.TestLoader().loadTestsFromModule(mod)
            print('\n\nRunning', m)
            result = unittest.TextTestRunner(verbosity=2).run(suite)
            if not result.wasSuccessful():
                from sys import stderr
                print('\n\nOne (or more) unit tests FAILED', file=stderr)
                return -1
        print('All tests successfully PASSED')
        return 0
            
    if args.command == 'check':
        # fake a job id so that epmt_check doesn't fail because of a missing job id
        environ['SLURM_JOB_ID'] = '1'
        return(0 if epmt_check() else 1)
    if args.command == 'daemon':
        from epmt_daemon import start_daemon, stop_daemon, daemon_loop, print_daemon_status
        if args.start or args.foreground:
            return daemon_loop() if args.foreground else start_daemon()
        elif args.stop:
            return stop_daemon()
        else:
            return print_daemon_status()
    # submit does the drop on its own, so here we handle
    if args.command == 'drop':
        if (not(args.force)):
            confirm = input("This will drop the entire database. This action cannot be reversed. Are you sure (yes/NO): ")
            if (confirm.upper() not in ('Y', 'YES')):
                return 0
        logger.info('request to drop all data in the database')
        from orm import orm_drop_db
        orm_drop_db()
        return 0
    if args.command == 'dbsize':
        return(epmt_dbsize(args.epmt_cmd_args, usejson=args.json, usebytes=args.bytes) == False)
    if args.command == 'start':
        return(epmt_start_job(other=args.epmt_cmd_args) == False)
    if args.command == 'stop':
        return(epmt_stop_job(other=args.epmt_cmd_args) == False)
    if args.command == "stage":
        return(epmt_stage(args.epmt_cmd_args,keep_going=not args.error) == False)
    if args.command == 'run':
        return(epmt_run(args.epmt_cmd_args,wrapit=args.auto,dry_run=args.dry_run,debug=(args.verbose > 2)))
    if args.command == 'source':
        s = epmt_source(slurm_prolog=args.slurm,papiex_debug=(args.verbose > 2),monitor_debug=(args.verbose > 3))
        if not s:
            return(1)
        print(s,end="")
        return(0)
    if args.command == 'dump':
        return(epmt_dump_metadata(args.epmt_cmd_args) == False)
    if args.command == 'submit':
        return(epmt_submit(args.epmt_cmd_args,dry_run=args.dry_run,drop=args.drop,keep_going=not args.error, ncpus = args.num_cpus) == False)
    if args.command == 'check':
        return(epmt_check() == False)
    if args.command == 'delete':
        from epmt_cmd_delete import epmt_delete_jobs
        return(epmt_delete_jobs(args.epmt_cmd_args) == False)
    if args.command == 'list':
        from epmt_cmd_list import epmt_list
        return(epmt_list(args.epmt_cmd_args) == False)
    if args.command == 'notebook':
        from epmt_cmd_notebook import epmt_notebook
        return(epmt_notebook(args.epmt_cmd_args) == False)

    logger.error("Unknown command, %s. See -h for options.",args.command)
    return(1)
