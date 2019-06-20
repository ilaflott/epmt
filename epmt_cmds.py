#!/usr/bin/env python
from datetime import datetime
from os import environ, makedirs, mkdir, errno, path, getpid, getuid, getsid, getcwd, chdir
from socket import gethostname
#from json import dumps as dict_to_json
from subprocess import call as forkexecwait
from random import randint
from imp import find_module
from grp import getgrall, getgrgid
from pwd import getpwnam, getpwuid
from glob import glob
from sys import stdout, stderr
from shutil import rmtree
import fnmatch
import pickle
from logging import getLogger, basicConfig, DEBUG, INFO, WARNING, ERROR
logger = getLogger(__name__)  # you can use other name

if environ.get('EPMT_USE_DEFAULT_SETTINGS'):
    #logger.info('Overriding settings.py and using defaults in epmt_default_settings')
    import epmt_default_settings as settings
else:
    import settings

def init_settings():
    global settings
    for k in [ "provider", "user", "password", "host", "dbname", "filename" ]:
        name = "EPMT_DB_"+ k.upper()
        t = environ.get(name)
        if t:
            logger.info("%s found, setting %s:%s now %s:%s",name,k,settings.db_params[k],k,t)
            settings.db_params[k] = t

    if not hasattr(settings, 'job_tags_env'):
        logger.warning("missing settings.job_tags_env")
        settings.job_tags_env = 'EPMT_JOB_TAGS'
    if not hasattr(settings, 'tag_delimiter'):
        logger.warning("missing settings.tag_delimiter")
        settings.tag_delimiter = ';'
    if not hasattr(settings, 'tag_kv_separator'):
        logger.warning("missing settings.tag_kv_separator")
        settings.tag_kv_separator = ':'
    if not hasattr(settings, 'tag_default_value'):
        logger.warning("missing settings.tag_default_value")
        settings.tag_default_value = "1"
    if not hasattr(settings, 'jobid_env_list'):
        logger.warning("missing settings.jobid_env_list")
        settings.jobid_env_list = [ "SLURM_JOB_ID", "SLURM_JOBID", "PBS_JOB_ID" ]
    if not hasattr(settings, 'verbose'):
        logger.warning("missing settings.verbose")
        settings.verbose = 0
    if not hasattr(settings, 'stage_command'):
        logger.warning("missing settings.stage_command ")
        settings.stage_command = "cp"
    if not hasattr(settings, 'stage_command_dest'):
        logger.warning("missing settings.stage_command_dest")
        settings.stage_command_dest = "."
    if not hasattr(settings, 'per_process_fields'):
        logger.warning("missing settings.per_process_fields")
        settings.per_process_fields = ["tags","hostname","exename","path","args","exitcode","pid","generation","ppid","pgid","sid","numtids"]
    if not hasattr(settings, 'skip_for_thread_sums'):
        logger.warning("missing settings.skip_for_thread_sums")
        settings.skip_for_thread_sums = ["tid", "start", "end", "num_threads", "starttime"]
    if not hasattr(settings, 'proc_sums_field_in_job'):
        logger.warning("missing settings.proc_sums_field_in_job")
        settings.proc_sums_field_in_job = 'proc_sums'
    if not hasattr(settings, 'thread_sums_field_in_proc'):
        logger.warning("missing settings.thread_sums_field_in_proc")
        settings.thread_sums_field_in_proc = 'threads_sums'
    if not hasattr(settings, 'all_tags_field'):
        logger.warning("missing settings.all_tags_field")
        settings.all_tags_field = 'all_proc_tags'

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

# Remove those with _ at beginning
def blacklist_filter(filter=None, **env):
#	print env
	env2 = {}
	for k, v in env.iteritems():
		if k.startswith("_"):
                    continue
		if k == "LS_COLORS":
                    continue
                env2[k] = v
	return env2

def dump_config(outf):
    print >> outf,"\nsettings.py (affected by the below env. vars):"
#    book = {}
    for key, value in sorted(settings.__dict__.iteritems()):
        if not (key.startswith('__') or key.startswith('_')):
            print >> outf,"%-24s%-56s" % (key,str(value))
    print >> outf,"\nenvironment variables (overrides settings.py):"
    for v in [ "PAPIEX_OSS_PATH", "PAPIEX_OUTPUT", "EPMT_DB_PROVIDER", "EPMT_DB_USER", "EPMT_DB_PASSWORD", "EPMT_DB_HOST", "EPMT_DB_DBNAME", "EPMT_DB_FILENAME" ]:
#                "provider", "user", "password", "host", "dbname", "filename" ]:
# "PAPIEX_OPTIONS","PAPIEX_DEBUG","PAPI_DEBUG","MONITOR_DEBUG","LIBPFM_DEBUG"
#              ]:
        if v in environ:
            print >> outf,"%-24s%-56s" % (v,environ[v])

def merge_two_dicts(x, y):
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z

def read_job_metadata_direct(file):
    data = pickle.load(file)
    logger.debug("Unpickled")
    return data

def read_job_metadata(jobdatafile):
    logger.info("Unpickling from "+jobdatafile)
    with open(jobdatafile,'rb') as file:
        return read_job_metadata_direct(file)
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
    print "\t" + bcolors.FAIL + "Fail" + bcolors.ENDC
def PrintPass():
    print "\t" + bcolors.OKBLUE + "Pass" + bcolors.ENDC
def PrintWarning():
    print "\t" + bcolors.WARNING + "Pass" + bcolors.ENDC

def verify_install_prefix():
    str = settings.install_prefix
    print "settings.install_prefix =",str
    retval = True
# Check for bad stuff and shortcut
    if "*" in str or "?" in str:
        logger.error("Found wildcards in value!",str)
        PrintFail()
        return False
    for e in [ "lib/libpapiex.so","lib/libmonitor.so",
               "lib/libpapi.so","lib/libpfm.so","bin/papi_command_line" ]:
        cmd = "ls -l "+str+e+">/dev/null"
        logger.info("\t"+cmd)
        return_code = forkexecwait(cmd, shell=True)
        if return_code != 0:
            retval = False

    if retval == True:
        PrintPass()
    else:
        PrintFail()
    return retval
    
def verify_papiex_output():
    str = settings.papiex_output
    print "settings.papiex_output =",str
    retval = True
# Check for bad stuff and shortcut
    if "*" in str or "?" in str:
        logger.error("Found wildcards in value!",str)
        PrintFail()
        return False
# Print and create dir
    def testdir(str2):
        logger.info("\tmkdir -p "+str2)
        return(create_job_dir(str2))
# Test create (or if it exists)
    if testdir(str) == False:
        retval = False
# Test make a subdir
    if testdir(str+"tmp") == False:
        retval = False
# Test to make sure we can access it
    cmd = "ls -lR "+str+" >/dev/null"    
    logger.info("\t"+cmd)
    return_code = forkexecwait(cmd, shell=True)
    if return_code != 0:
        retval = False
# Remove the created tmp dir
    cmd = "rm -rf "+str+"tmp"
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
    print "settings.papiex_options =",str
    retval = True
# Check for any components
    cmd = settings.install_prefix+"bin/papi_component_avail"+"| sed -n -e '/Active/,$p' | grep perf_event >/dev/null"
    logger.info("\t"+cmd)
    return_code = forkexecwait(cmd, shell=True)
    if return_code != 0:
        retval = False
# Now check events
    eventlist = str.split(',')
    for e in eventlist:
        cmd = settings.install_prefix+"bin/papi_command_line "+e+"| sed -n -e '/PERF_COUNT_SW_CPU_CLOCK\ :/,$p' | grep PERF_COUNT_SW_CPU_CLOCK > /dev/null"
        logger.info("\t"+cmd)
        return_code = forkexecwait(cmd, shell=True)
        if return_code != 0:
            retval = False
# End
    if retval == True:
        PrintPass()
    else:
        PrintFail()
    return retval

def verify_db_params():
    print "settings.db_params =",str(settings.db_params)
    try:
        from epmt_job import setup_orm_db
        if setup_orm_db(settings) == False:
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
    print f,"exists and has a value of 0"
    try:
        with open(f, 'r') as content_file:
            value = int(content_file.read())
            logger.info("%s = %d",f,value)
            if value != 0:
                logger.error("bad %s value of %d, should be 0 to allow cpu events",f,value)
                PrintFail()
                return False
            logger.info("perf_event_paranoid is %d",value)
            PrintPass()
            return True
    except Exception as e:
        print >> stderr,str(e)
        PrintFail()
    return False

def verify_papiex():
    print "epmt run functionality"
    logger.info("\tepmt run -a /bin/sleep 1")
    fake_job_id = "1"
    dir = settings.papiex_output+fake_job_id+"/"
    retval = epmt_run(fake_job_id,["/bin/sleep","1"],wrapit=True)
    if retval != 0:
        PrintFail()
        return False
    files = glob(dir+settings.input_pattern)
    if len(files) != 1:
        logger.error("%s matched %d papiex CSV output files instead of 1",dir+settings.input_pattern,len(files))
        PrintFail()
        rmtree(dir)
        return False
    files = glob(dir+"job_metadata")
    if len(files) != 1:
        logger.error("%s matched %d job_metadata files instead of 1",dir+job_metadata,len(files))
        PrintFail()
        rmtree(dir)
        return False
    rmtree(dir)
    PrintPass()
    return True

def epmt_check():
    retval = True
    if verify_db_params() == False:
        retval = False
    if verify_install_prefix() == False:
        retval = False
    if verify_papiex_output() == False:
        retval = False
    if verify_perf() == False:
        retval = False
    if verify_papiex_options() == False:
        retval = False
    if verify_papiex() == False:
        retval = False
    return retval

#
# These two functions should match _check_and_create_metadata!
#

def create_start_job_metadata(jobid, submit_ts, from_batch=[]):
	ts=datetime.now()
	metadata = {}
	start_env=blacklist_filter(filter,**environ)
#	print env
	metadata['job_pl_id'] = jobid
#	metadata['job_pl_hostname'] = gethostname()
        if submit_ts == False:
            metadata['job_pl_submit_ts'] = ts
        else:
            metadata['job_pl_submit_ts'] = submit_ts
	metadata['job_pl_start_ts'] = ts
	metadata['job_pl_env'] = start_env
#        metadata['job_pl_from_batch'] = from_batch
	return metadata

def merge_stop_job_metadata(metadata, exitcode, reason, from_batch=[]):
    ts=datetime.now()
    stop_env=blacklist_filter(filter,**environ)
    metadata['job_el_stop_ts'] = ts
#    metadata['job_el_from_batch'] = from_batch
    metadata['job_el_exitcode'] = exitcode
    metadata['job_el_reason'] = reason
    metadata['job_el_env'] = stop_env
    return metadata

def get_jobid():
    if hasattr(settings, 'jobid_env_list'):
        for e in settings.jobid_env_list:
            jid = environ.get(e)
            if jid:
                return jid
        logger.error("No valid jobid found in pattern %s, consider using -j <jobid>",settings.jobid_env_list)
        return False
    logger.error("No valid job_id_env_list found in settings.py")
    return False

def get_job_dir(jobid):
    return settings.papiex_output + jobid + "/"

def get_job_metadata_file(dirwithslash):
    return dirwithslash+"job_metadata"

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

def setup_vars(forced_jobid):
    if forced_jobid:
        jobid = forced_jobid
    else:
        jobid = get_jobid()
    if jobid is False:
        return False,False,False
    dir = get_job_dir(jobid)
    file = get_job_metadata_file(dir)
    logger.info("jobid = %s, dir = %s, file = %s",jobid,dir,file)
    return jobid,dir,file

def epmt_start_job(forced_jobid,other=[]):
    jobid,dir,file = setup_vars(forced_jobid)
    if jobid == False:
        return False;
    metadata = create_start_job_metadata(jobid,False,other)
    if create_job_dir(dir) is False:
        return False
    if path.exists(file):
        logger.error("%s already exists!",file)
        return False
    retval = write_job_metadata(file,metadata)
    return retval

def epmt_stop_job(forced_jobid,other=[]):
    jobid,dir,file = setup_vars(forced_jobid)
    if jobid == False:
        return False;
    start_metadata = read_job_metadata(file)
    if not start_metadata:
        return False
    logger.info("read job start metadata from %s",file);
    if "job_el_stop_ts" in start_metadata:
        logger.error("%s is already complete!",file)
        return False
    metadata = merge_stop_job_metadata(start_metadata,0,"none",other)
    retval = write_job_metadata(file,metadata)
    return retval

def epmt_dump_metadata(forced_jobid, filelist=[]):
# If no file specified, then try and find it
#    if len(filelist) == 0:
    if len(filelist) is 0:
        jobid,dir,file = setup_vars(forced_jobid)
        if jobid == False:
            return False;
        filelist = [file]

    
    for file in filelist:
        if not path.exists(file):
            logger.error("%s does not exist!",file)
            exit(1)

        tar = compressed_tar(file)
        if tar:
            try:
                info = tar.getmember("./job_metadata")
            except KeyError:
                logger.error('ERROR: Did not find %s in tar archive' % "job_metadata")
                exit(1)
            else:
                logger.info('%s is %d bytes in archive' % (info.name, info.size))
                f = tar.extractfile(info)
                metadata = read_job_metadata_direct(f)
        else:
            metadata = read_job_metadata(file)
            print metadata

        if not metadata:
            return False
        for d in sorted(metadata.keys()):
            print "%-24s%-56s" % (d,str(metadata[d]))
    return True

def epmt_source(forced_jobid, papiex_debug=False, monitor_debug=False, add_export=True, run_cmd=False):
    export="export "
    equals="="
    cmd_sep="\n"
    cmd=""

    # For CSH, for source:
    # setenv FOO bar;
    # For CSH, for run:
    # env FOO=bar

    shell_name = environ.get("_")
    shell_name2 = environ.get("SHELL")
    if ( shell_name2 and shell_name2.endswith("csh")) or (shell_name and shell_name.endswith("csh")):
        logger.debug("Detected CSH - please read CSH considered harmful")
        if run_cmd:
            cmd = "env "
            export = ""
            equals = "="
        else:
            export="setenv "
            equals= " "
            cmd_sep=";\n"
    
    jobid,output_dir,file = setup_vars(forced_jobid)
    if jobid == False:
        return None;

    if add_export:
        cmd = export
    cmd += "PAPIEX_OPTIONS"+equals+settings.papiex_options
    if add_export:
        cmd += cmd_sep
    else:
        cmd += " "
    
    if output_dir:
        if add_export:
            cmd += export
        cmd += "PAPIEX_OUTPUT"+equals+output_dir
        if add_export:
            cmd += cmd_sep
        else:
            cmd += " "

    if papiex_debug:
        if add_export:
            cmd += export
        cmd += "PAPIEX_DEBUG"+equals+"TRUE"
        if add_export:
            cmd += cmd_sep
        else:
            cmd += " "

    if monitor_debug:
        if add_export:
            cmd += export
        cmd += "MONITOR_DEBUG"+equals+"TRUE"
        if add_export:
            cmd += cmd_sep
        else:
            cmd += " "

    if add_export:
        cmd += export
    cmd += "LD_PRELOAD"+equals
    for l in [ "libpapiex.so:","libpapi.so:","libpfm.so:","libmonitor.so" ]:
        cmd += settings.install_prefix+"lib/"+l
    return cmd

def epmt_run(forced_jobid, cmdline, wrapit=False, dry_run=False, debug=False):
    logger.debug("epmt_run(%s, %s, %s, %s, %s)",forced_jobid, cmdline, str(wrapit), str(dry_run), str(debug))
    if wrapit:
        logger.info("Forcing epmt_start")
        if dry_run:
            print "epmt start"
        else:
            if not epmt_start_job(forced_jobid):
                return 1

    cmd = epmt_source(forced_jobid, papiex_debug=debug, monitor_debug=debug, add_export=False, run_cmd=True)
    if not cmd:
        return 1 
    cmd += " "+" ".join(cmdline)

    logger.info("Executing(%s)",cmd)
    if not dry_run:
        return_code = forkexecwait(cmd, shell=True)
        logger.info("Exit code %d",return_code)
    else:
        print cmd
        return_code = 0

    if wrapit:
        logger.info("Forcing epmt_stop")
        if dry_run:
            print "epmt stop"
        else:
            epmt_stop_job(forced_jobid)

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
        if filedict.get(host):
            filedict[host].append(f)
        else:
            filedict[host] = [ f ]
    if dumperr:
        logger.warn("Host not found in name split, using unknown host")

    return filedict

def epmt_submit(other_dirs, forced_jobid=None, dry_run=True, drop=False, keep_going=True):
    if dry_run and drop:
        logger.error("You can't drop tables and do a dry run")
        return(False)
    if other_dirs and forced_jobid:
        logger.error("You can't force a job id and provide a list of directories")
        return(False)
    if other_dirs: # specified list of dirs
        for f in other_dirs:
            r = submit_to_db(f,settings.input_pattern,dry_run=dry_run,drop=drop)
            if r is False and not keep_going:
                return(r)
        return(True)
    else:
        jobid,dir,file = setup_vars(forced_jobid)
        if jobid is False:
            return(False)
        return(submit_to_db(dir,settings.input_pattern,dry_run=dry_run,drop=drop))
        

def compressed_tar(input):
    tar = None
    if (input.endswith("tar.gz") or input.endswith("tgz")):
        import tarfile
        tar = tarfile.open(input, "r:gz")
    elif (input.endswith("tar")):
        import tarfile
        tar = tarfile.open(input, "r:")
    return tar
    
# Compute differences in environment if detected
# Merge start and stop environments
#    total_env = start_env.copy()
#    total_env.update(stop_env)
# Check for Experiment related variables
#    metadata = check_and_add_workflowdb_envvars(metadata,total_env)

def submit_to_db(input, pattern, dry_run=True, drop=False):
#    if not jobid:
#        logger.error("Job ID is empty!");
#        exit(1);

    logger.info("submit_to_db(%s,%s,%s)",input,pattern,str(dry_run))

    tar = compressed_tar(input)
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
            return False
        else:
            logger.info('%s is %d bytes in archive' % (info.name, info.size))
            f = tar.extractfile(info)
            metadata = read_job_metadata_direct(f)
            filedict = get_filedict(None,settings.input_pattern,tar)
    else:
        metadata = read_job_metadata(input+"job_metadata")
        filedict = get_filedict(input,settings.input_pattern)

    logger.info("%d hosts found: %s",len(filedict.keys()),filedict.keys())
    for h in filedict.keys():
        logger.info("host %s: %d files to import",h,len(filedict[h]))

# Do as much as we can before bailing
    if dry_run:
#        check_workflowdb_dict(metadata,pfx="exp_")
        logger.info("Dry run finished, skipping DB work")
        return

#    if tar:
#        tar.close()
#        logger.error('Unsupported at the moment.')
#        exit(1)

# Now we touch the Database
    from epmt_job import setup_orm_db, ETL_job_dict
    if setup_orm_db(settings) == False:
        return False
    j = ETL_job_dict(metadata,filedict,settings,tarfile=tar)
    if not j:
        return False
    logger.info("Committed job %s to database: %s",j.jobid,j)

# Dead code
# Check if we have anything related to an "experiment"
#
#    if check_workflowdb_dict(metadata,pfx="exp_"):
#        e = ETL_ppr(metadata,j.jobid)
#        if not e:
#            exit(1)
#        logger.info("Committed post process run to database")    

def set_logging(intlvl = 0):
    if intlvl < 0:
        basicConfig(level=ERROR)
    if intlvl == 0:
        basicConfig(level=WARNING)
    if intlvl == 1:
        basicConfig(level=INFO)
    elif intlvl >= 2:
        basicConfig(level=DEBUG)

def stage_job(jid,dir,file,collate,compress_and_tar=True):
    logger.debug("stage_job(%s,%s,%s,%s)",jid,dir,file,str(collate))
    if not jid or len(jid) < 1:
        return False
    if not dir or len(dir) < 1:
        return False
    if not file or len(file) < 1:
        return False
    if settings.stage_command and len(settings.stage_command) and settings.stage_command_dest and len(settings.stage_command_dest):
        if collate:
            from epmt_concat import csvjoiner
            logger.debug("csvjoiner(%s)",dir)
            hack_dir = getcwd()
            status, collated_file = csvjoiner(dir,debug="false")
            chdir(hack_dir)
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
                cmd = "cp -p "+collated_file+" "+newdir
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
        if compress_and_tar:
            cmd = "tar -C "+dir+" -cz -f "+path.dirname(dir)+".tgz ."
            logger.debug(cmd)
            return_code = forkexecwait(cmd, shell=True)
            if return_code != 0:
                return False
            dir=path.dirname(dir)+".tgz "
        cmd = settings.stage_command + " " + dir + " " + settings.stage_command_dest
        logger.debug(cmd)
        return_code = forkexecwait(cmd, shell=True)
        if return_code != 0:
            return False
        print(settings.stage_command_dest+path.basename(dir))
    return True

def epmt_stage(other_dirs, forced_jobid, collate=True):
    logger.debug("epmt_stage(%s,%s,%s)",forced_jobid,other_dirs,str(collate))
    if other_dirs:
        for dir in other_dirs:
            if not dir.endswith("/"):
                logger.warning("missing trailing / on %s",dir)
                dir += "/"
            jobid = path.basename(path.dirname(dir))
            file = dir + "job_metadata"
            r = stage_job(jobid,dir,file,collate)
            if r is False:
                return False
        return True
    else:
        jobid,dir,file = setup_vars(forced_jobid)
        return(stage_job(jobid,dir,file,collate))

#
# depends on args being global
#
def epmt_entrypoint(args, help):
    set_logging(args.verbose)
    init_settings()
    if not args.verbose:
        set_logging(settings.verbose)

    if args.help or args.epmt_cmd == 'help' or not args.epmt_cmd:
        help(stdout)
        dump_config(stdout)
        exit(0)

    if args.epmt_cmd == 'start':
        return(epmt_start_job(args.jobid,other=args.epmt_cmd_args) == False)
    if args.epmt_cmd == 'stop':
        return(epmt_stop_job(args.jobid,other=args.epmt_cmd_args) == False)
    if args.epmt_cmd == 'dump':
        return(epmt_dump_metadata(args.jobid,filelist=args.epmt_cmd_args) == False)
    if args.epmt_cmd == 'source':
        s = epmt_source(args.jobid,(args.verbose > 2),monitor_debug=(args.verbose > 2),add_export=True)
        if s:
            print(s)
            return 0
        return 1
    if args.epmt_cmd == "stage":
        return(epmt_stage(args.epmt_cmd_args,args.jobid) == False)
    if args.epmt_cmd == 'run':
        if not args.epmt_cmd_args: 
            logger.error("No command given")
            return(1)
        return(epmt_run(args.jobid,args.epmt_cmd_args,wrapit=args.auto,dry_run=args.dry_run,debug=(args.verbose > 2)))
    if args.epmt_cmd == 'submit':
        return(epmt_submit(args.epmt_cmd_args,args.jobid,dry_run=args.dry_run,drop=args.drop,keep_going=not args.error) == False)
    if args.epmt_cmd == 'check':
        return(epmt_check() == False)

    logger.error("Unknown command, %s. See -h for options.",args.epmt_cmd)
    exit(1)

# Use of globals here is gross. FIX!
# 
# if (__name__ == "__main__"):

