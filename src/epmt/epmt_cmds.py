#!/usr/bin/env python
from __future__ import print_function
from datetime import datetime
from os import environ, makedirs, mkdir, path, getpid, chdir, remove,  uname, kill
from socket import gethostname
from subprocess import run
from glob import glob
from sys import stderr
from json import dumps, loads
from shutil import copyfile, rmtree, move
import errno
import fnmatch
import pickle
from logging import getLogger
from epmt.orm import db_session

logger = getLogger(__name__)  # you can use other name
import epmt.epmt_settings as settings
from epmt.epmtlib import get_username, epmt_logging_init, init_settings, conv_dict_byte2str, cmd_exists, run_shell_cmd, safe_rm, dict_filter, check_fix_metadata, logfn

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


def dump_config(outf, sep = ":"):
    print("\nsettings.py:", file=outf)
#    book = {}
    for key, value in sorted(settings.__dict__.items()):
        if not (key.startswith('__') or key.startswith('_') or key == 'ERROR'):
            if type(value) in [str, int, float, list, dict, bool]:
                print("%s%s%s" % (key,sep,str(value)), file=outf)
    print("\nenvironment variables (overrides settings.py):", file=outf)
    for v in [ "PAPIEX_OSS_PATH", "PAPIEX_OUTPUT", "EPMT_DB_PROVIDER", "EPMT_DB_USER", "EPMT_DB_PASSWORD", "EPMT_DB_HOST", "EPMT_DB_DBNAME", "EPMT_DB_FILENAME" ]:
#                "provider", "user", "password", "host", "dbname", "filename" ]:
# "PAPIEX_OPTIONS","PAPIEX_DEBUG","PAPI_DEBUG","MONITOR_DEBUG","LIBPFM_DEBUG"
#              ]:
        if v in environ:
            print("%s%s%s" % (v,sep,environ[v]), file=outf)

@logfn
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

@logfn
def read_job_metadata(jobdatafile):
    logger.info("Unpickling from "+jobdatafile)
    try:
        with open(jobdatafile,'rb') as file:
            return read_job_metadata_direct(file)
    except IOError as i:
        logger.info("%s", str(i))
    return False

def write_job_epilog(jobdatafile,metadata):
    with open(jobdatafile,'w+b') as file:
        pickle.dump(metadata,file)
        logger.debug("Pickled to "+jobdatafile)
        return True
    return False

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
    for e in [ "/lib/libpapiex.so","/lib/libmonitor.so",
               "/lib/libpapi.so","/lib/libpfm.so","/bin/papi_command_line" ]:
        cmd = "ls -l "+install_prefix+e+">/dev/null 2>&1"
        logger.info("\t"+cmd)
        return_code = run(cmd, shell=True).returncode
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
    return_code = run(cmd, shell=True).returncode
    if return_code != 0:
        retval = False
# Remove the created tmp dir
    cmd = "rm -rf "+opf+"tmp"
    logger.info("\t"+cmd)
    return_code = run(cmd, shell=True).returncode
    if return_code != 0:
        retval = False
# Cleanup
    if retval == True:
        PrintPass()
    else:
        PrintFail()
    return retval


def verify_papiex_options():
    s = get_papiex_options(settings)
    #print("papiex_options =",s, end='')
    logger.info(f'papiex_options = {s}')
    logger.info(f'settings.install_prefix = {settings.install_prefix}')
    retval = True
# Check for any components
#    cmd = settings.install_prefix+"/bin/papi_component_avail 2>&1 "+"| sed -n -e '/Active/,$p' | grep perf_event >/dev/null 2>&1"
    cmd = settings.install_prefix+"/bin/papi_component_avail 2>&1 "+"| sed -e '/Active/,$p' | grep perf_event >/dev/null 2>&1"
    logger.info("\t"+cmd)
    return_code = run(cmd, shell=True).returncode
    if return_code != 0:
        logger.error("%s failed",cmd)
        retval = False
# Now check events, deduplicate extra commas and remove empty list elements
    eventlist = s.split(',')
    for e in eventlist:
        if e in [ 'COLLATED_TSV', 'DEBUG' ]:
            continue
#        cmd = settings.install_prefix+"/bin/papi_command_line 2>&1 "+e+"| sed -n -e '/PERF_COUNT_SW_CPU_CLOCK\ :/,$p' | grep PERF_COUNT_SW_CPU_CLOCK > /dev/null 2>&1" # does not work for rocky-8. 
        cmd = settings.install_prefix+"/bin/papi_command_line 2>&1 "+e+"| sed -e '/PERF_COUNT_SW_CPU_CLOCK\ :/,$p' | grep PERF_COUNT_SW_CPU_CLOCK > /dev/null 2>&1" # guessing... NOT TRIED YET TODO: TRY THIS INSTEAD OF ABOVE LINE
        logger.info("\t"+cmd)
        return_code = run(cmd, shell=True).returncode
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
        from epmt.orm import setup_db
        if setup_db(settings) == False:
            PrintFail()
            return False
        else:
            PrintPass()
            return True
    except ImportError as e:
        logger.error("Error setting up DB: {}".format(str(e)))
        PrintFail()
        return False
    
def verify_perf():
    f="/proc/sys/kernel/perf_event_paranoid"
    print(f,end='')
    try:
        with open(f, 'r') as content_file:
            value = int(content_file.read())
            print(" = ",value, end='')
            if value > 2:
                logger.error("bad %s value of %d, 2 or less to allow perf subsystem events",f,value)
                PrintFail()
                return False
            logger.info("perf_event_paranoid is %d",value)
            PrintPass()
            return True
    except Exception as e:
        logger.error(str(e))
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
    logger.info("\tepmt run -a /bin/sleep 1")
    retval = epmt_run(["/bin/sleep","1"],wrapit=True)
    global_jobid,global_datadir,global_metadatafile = setup_vars()
    if retval != 0:
        retval = False
    else:
        retval = True
        files = glob(global_datadir+settings.input_pattern)
        if 'COLLATED_TSV' in get_papiex_options(settings):
            num_to_find = 2 # We have a header file that matches the pattern in this case, sadly
        else:
            num_to_find = 1
        if len(files) != num_to_find:
            logger.error("%s matched %d papiex output files instead of %d",
                         global_datadir+settings.input_pattern,len(files),num_to_find)
            retval = False
    if retval == True:
        files = glob(global_datadir+"job_metadata")
        if len(files) != 1:
            logger.error("%s matched %d job_metadata files instead of 1",global_datadir+"job_metadata",len(files))
            retval = False

    logger.info("rmtree %s",global_datadir) 
    rmtree(global_datadir, ignore_errors=True)

    if retval == True:
        PrintPass()
    else:
        PrintFail()
    return retval

def epmt_check():
    retval = True
    logger.warning('CHECKING verify_db_params()...')
    if verify_db_params() == False:
        retval = False
    logger.warning('CHECKING verify_install_prefix()...')
    if verify_install_prefix() == False:
        retval = False
    logger.warning('CHECKING verify_epmt_output_prefix()...')
    if verify_epmt_output_prefix() == False:
        retval = False
    logger.warning('CHECKING verify_perf()...')
    if verify_perf() == False:
        retval = False
    logger.warning('CHECKING verify_papiex_options()...')
    if verify_papiex_options() == False:
        retval = False
    logger.warning('CHECKING verify_stage_command()...')
    if verify_stage_command() == False:
        retval = False
    logger.warning('CHECKING verify_papiex()...')
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
    try:
        # this should normally never fail
        metadata['job_pl_hostname'] = gethostname() or uname()[1]
    except:
        pass
    return metadata

def merge_stop_job_metadata(metadata, exitcode=0, reason="none", from_batch=[]):
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
            logger.error("dir %s: %s",dir,str(e))
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
        logger.error("No job id (%s) was found in environment",str(settings.jobid_env_list))
        return False

    jobid = get_jobid()
    if not jobid:
        return False,False,False

    dir = settings.epmt_output_prefix + get_username() + "/" + jobid + "/"
    file = dir + "job_metadata"
    logger.info("jobid = %s, dir = %s, file = %s",jobid,dir,file)
    return jobid,dir,file

# Append .tmp to filename
def started_metadata_file(filename):
    return filename + ".tmp"
def stopped_metadata_file(filename):
    return filename

@logfn
def epmt_start_job(keep_going=True,other=[]):
    global_jobid,global_datadir,global_metadatafile = setup_vars()
    if not (global_jobid and global_datadir and global_metadatafile):
        return False
    if path.exists(started_metadata_file(global_metadatafile)):
        logger.info(started_metadata_file(global_metadatafile))
        # this means we are calling epmt start again
        # let's be tolerant and issue a warning, but not flag this as an error
        if keep_going:
            logger.warning("job is already started, ignoring")
            return True
        else:
            logger.error("job is already started")
            return False
    if path.exists(stopped_metadata_file(global_metadatafile)):
        # this means we are calling epmt start after a stop, this is not supported
        logger.info(stopped_metadata_file(global_metadatafile))
        if keep_going:
            logger.warning("job is already complete, ignoring")
            return True
        else:
            logger.error("job is already complete")
            return False
    if create_job_dir(global_datadir) is False:
        return False
    metadata = create_start_job_metadata(global_jobid,False,other)
    return write_job_metadata(started_metadata_file(global_metadatafile),metadata)

@logfn
def epmt_stop_job(keep_going=True, other=[]):
    global_jobid,global_datadir,global_metadatafile = setup_vars()
    if not (global_jobid and global_datadir and global_metadatafile):
        return False

    if path.exists(stopped_metadata_file(global_metadatafile)):
        # this means we are calling epmt start after a stop, this is not supported
        logger.info(stopped_metadata_file(global_metadatafile))
        if keep_going:
            logger.warning("job is already complete, ignoring")
            return True
        else:
            logger.error("job is already complete")
            return False

    start_metadata = read_job_metadata(started_metadata_file(global_metadatafile))
    if not start_metadata:
        logger.info(started_metadata_file(global_metadatafile))
        logger.error("job is not started")
        return False

    metadata = merge_stop_job_metadata(start_metadata)
    checked_metadata = check_fix_metadata(metadata)
    if not checked_metadata:
        return False
    logger.debug("Removing %s, job stop complete",started_metadata_file(global_metadatafile))
    remove(started_metadata_file(global_metadatafile))
    return write_job_metadata(stopped_metadata_file(global_metadatafile),checked_metadata)

@logfn
def epmt_dump_metadata(filelist, key = None):
    rc_final = True
    if not filelist:
        global_jobid,global_datadir,global_metadatafile = setup_vars()
        if not (global_jobid and global_datadir and global_metadatafile):
            return False
        if path.exists(stopped_metadata_file(global_metadatafile)):
            logger.debug("this job has been stopped")
            filelist = [stopped_metadata_file(global_metadatafile)]
        elif path.exists(started_metadata_file(global_metadatafile)):
            logger.debug("this job has been started, not stopped")
            filelist = [started_metadata_file(global_metadatafile)]
        else:
            logger.error('dump cannot be called before start without an explicit directory')
            return False
        
    if len(filelist) < 1:
        logger.error("Could not identify your job id")
        return False

    for f in filelist:
        logger.info('Processing {}'.format(f))

        if not path.exists(f):
            if ('/' in f) or ('.tgz' in f):
                logger.error("%s does not exist!",f)
                return False
            logger.debug('{} was not found in the file-system. Checking database..'.format(f))
            from epmt.epmt_cmd_show import epmt_show_job
            # if the file does not exist then we check the DB
            rc = epmt_show_job(f, key = key)
            if not(rc):
                rc_final = False
            continue

        err,tar = open_compressed_tar(f)
        if tar:
            try:
                info = tar.getmember("./job_metadata")
            except KeyError:
                logger.error('Did not find %s in tar file ' % "job_metadata")
                return False
            else:
                logger.info('%s is %d bytes in archive' % (info.name, info.size))
                f = tar.extractfile(info)
                metadata = read_job_metadata_direct(f)
        else:
            metadata = read_job_metadata(f)

        if not metadata:
            return False
        if key:
            print(metadata[key])
        else:
            for d in sorted(metadata.keys()):
                print("%-24s%-56s" % (d,str(metadata[d])))
    return rc_final

def annotate_metadata(metadatafile, annotations, replace = False):
    '''
    Annotate a metadata file

    Parameters
    ----------
         metadatafile: string
                       The path to the metadata file
          annotations: dict
                       Dictionary representing new annotations
              replace: boolean, optional
                       If set, the existing annotations will be completely
                       overwritten. Otherwise, the new annotations will be
                       merged in. Defaults to False.

    Returns
    -------
    True on success, False on error

    Notes
    -----
    This is a low-level function. You should use epmt_annotate instead
    where possible.
    '''
    if not path.isfile(metadatafile):
        logger.error('{} does not exist'.format(metadatafile))
        return False

    metadata = read_job_metadata(metadatafile)
    if not metadata:
        logger.error('Error reading metadata from {}'.format(metadatafile))
        return False

    # get existing annotations unless replace is set
    ann = metadata.get('annotations', {}) if (not replace) else {}
    # now merge in the new annotations, where the new annotations
    # will override existing annotations if keys are common
    ann.update(annotations)
    logger.debug('Updated annotations: {}'.format(ann))
    metadata['annotations'] = ann
    return write_job_metadata(metadatafile,metadata)

# args list is one of the following forms:
#   ['key1=value1', 'key2=value2', ...]  - annotate stopped job within a batch env
#   or 
#   ['111.tgz', 'key1=value1', 'key2=value2', ...] - annotate staged job file
#   or
#   ['658000', 'key1=value1', 'key2y=value2', ...] - annotate job in database
#
# Annotations are appended to unless replace is True, in which
# case existing annotations are wiped clean first.
 
def epmt_annotate(argslist, replace = False):
    if not argslist:
        return False # nothing to do

    from epmt.epmtlib import kwargify
    staged_file = job_dir = jobid = running_job = False  # initialize

    # this function returns the annotation dictionary from kwargs
    # with some error checking
    def get_annotations_from_kwargs(args):
        result = all("=" in elem for elem in args)
        if not result:
            logger.error("epmt_annotate: Annotations must be of the form <key>=<value>")
            return False
        ann = kwargify(args,strict=True)
        if not ann:
            logger.error("epmt_annotate: No annotations found. Annotations must be of the form <key>=<value>")
        return ann
        
   
    if '=' in argslist[0]:
        # if equals is in first argument, then we have no filename, we are annotating
        # a job specified in the batch environment. It must be already started.
        # The job may be stopped or not.
        annotations = get_annotations_from_kwargs(argslist)
        if not annotations:
            return False
        logger.info('annotating a job in the batch environment: {}'.format(annotations))
        jobid,datadir,metadatafile = setup_vars()
        if not (jobid and datadir and metadatafile):
            logger.error("jobid, datadir and metadatafile MUST be set in the environment")
            return False
        if path.exists(stopped_metadata_file(metadatafile)):
            metadatafile = stopped_metadata_file(metadatafile)
            logger.debug("this job has been stopped")
        elif path.exists(started_metadata_file(metadatafile)):
            metadatafile = started_metadata_file(metadatafile)
            logger.debug("this job has been started, not stopped")
        else:
            logger.error('annotate cannot be called before start')
            return False
    else:
        # No '=' in the first argument, that means the first
        # argument refers to either a staged job file, a directory or a job in db
        # the general format here is:
        #   <job/staged_file/dir> <key=value> [<key=value>]...
        annotations = get_annotations_from_kwargs(argslist[1:])
        if not annotations:
            return False

        arg0 = argslist[0]

        # Now based on arg0 we determine if we are dealing with which
        # of the following options:
        # a) staged file
        # b) job directory
        # c) job in database
        if arg0.endswith('.tgz'):
            # staged file form
            staged_file = arg0
            logger.info('annotating staged job file {0}: {1}'.format(staged_file, annotations))
            tempdir = extract_tar(staged_file, check_metadata = True)
            if not tempdir:
                logger.error('Error extracting {}'.format(staged_file))
                return False
            metadatafile = tempdir + "/job_metadata"

        elif path.isdir(arg0):
            # job directory form
            job_dir = arg0
            logger.info('annotating dir {}: {}'.format(job_dir, annotations))
            if path.exists(stopped_metadata_file(job_dir + "/job_metadata")):
                metadatafile = stopped_metadata_file(job_dir + "/job_metadata")
                logger.debug("job %s has been stopped",job_dir)
            elif path.exists(started_metadata_file(job_dir + "/job_metadata")):
                metadatafile = started_metadata_file(job_dir + "/job_metadata")
                logger.debug("job %s has been started, not stopped",job_dir)
            else:
                logger.error('annotate cannot be called before start')
                return False
            
        else:
            # database jobid form
            jobid = argslist[0]
            logger.info('annotating job {0} in db: {1}'.format(jobid, annotations))
            from epmt.epmt_query import annotate_job
            updated_ann = annotate_job(jobid, annotations, replace)
            logger.debug('updated annotations: {}'.format(updated_ann))
            if settings.job_tags_env in annotations:
                # we need to set <job>.tags to the value of EPMT_JOB_TAGS
                from epmt.epmt_query import tag_job
                # we have to overwrite the existing tags (not merge it in)
                r = tag_job(jobid, annotations[settings.job_tags_env], True)
                logger.debug('Updated tags for job {} to {}'.format(jobid, r))
            return annotations.items() <= updated_ann.items()

    # below we handle annotation update in the metadata file
    # if its a job in the batch environment, we simply write out 
    # the metadata and we are done. If it's a staged file then
    # we also need to recreate the tar.
    
    retval = annotate_metadata(metadatafile,annotations,replace=replace)
    if not retval:
        logger.error('Could not annotate metadatafile: ' + metadatafile)

    # for staged file case we need to recreate the .tgz file
    # but do not call stage!
    if staged_file:
        if retval:
            # create_tar will log an error if it failed
            retval = create_tar(staged_file, tempdir, remove_dir = True)

    return retval

# These two functions could be squashed into one.
def _papiex_opt_byhost(o):
    from re import match
    from re import error as reerror
    if hasattr(o,'papiex_options_byhost'):
        if type(o.papiex_options_byhost) == dict:
            hostname = gethostname()
            logger.info("hostname to match papiex_options_byhost is %s",hostname)
            for key, value in o.papiex_options_byhost.items():
                try:
                    if match(key,hostname):
                        logger.debug("%s matched %s",key,hostname)
                        options = value
                        return options
                except reerror:
                    logger.error("Invalid regular expression in papiex_options_bycpu: %s",key)
        else:
            logger.error("Unsupported type for papiex_options_byhost; must be a dictionary")
    return ""

def _papiex_opt_bycpu(o):
    from re import match
    from re import error as reerror
    if hasattr(o,'papiex_options_bycpu'):
        if type(o.papiex_options_bycpu) == dict:
            if o.papiex_options_bycpu:            
                from cpuinfo import get_cpu_info
                cpu_info = get_cpu_info()
                cpu_fms = str(cpu_info.get('family','no_family_found')) + "/" + str(cpu_info.get('model','no_model_found')) + "/" + str(cpu_info.get('stepping','no_stepping_found'))
                logger.info("cpu F/M/S to match papiex_options_bycpu is %s",cpu_fms)
                for key, value in o.papiex_options_bycpu.items():
                    try:
                        if match(key,cpu_fms):
                            logger.debug("%s matched %s",key,cpu_fms)
                            options = value
                            return options
                    except reerror:
                        logger.error("Invalid regular expression in papiex_options_bycpu: %s",key)
        else:
            logger.error("Unsupported type for papiex_options_bycpu; must be a dictionary")
    return ""

# We defer to CPU matches before HOSTNAME matches
def get_papiex_options(s):
    option_h = _papiex_opt_byhost(s)
    option_c = _papiex_opt_bycpu(s)
    option_d = s.papiex_options # The non-arch specific options
    option_hl = option_h.split(',')
    option_cl = option_c.split(',')
    option_dl = option_d.split(',')
    options = list(set(option_hl+option_cl+option_dl))
    return ','.join(filter(None, options))

@logfn
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
    cmd = add_var(cmd,"PAPIEX_OPTIONS"+equals+get_papiex_options(settings))
    old_pl_libs = environ.get("LD_PRELOAD","")
    papiex_pl_libs = settings.install_prefix+"/lib/libpapiex.so:"+settings.install_prefix+"/lib/libmonitor.so:"+settings.install_prefix+"/lib/libpapi.so:"+settings.install_prefix+"/lib/libpfm.so"
    if run_cmd:
        cmd = add_var(cmd,"LD_PRELOAD"+equals+papiex_pl_libs+":"+old_pl_libs)
    else:
        cmd = add_var(cmd,"PAPIEX_OLD_LD_PRELOAD"+equals+old_pl_libs)
        cmd = add_var(cmd,"PAPIEX_LD_PRELOAD"+equals+papiex_pl_libs)
#
# Use export -n which keeps the variable but prevents it from being exported
#
    if slurm_prolog:
        cmd += "export LD_PRELOAD="+papiex_pl_libs
        if len(old_pl_libs) > 0:
            cmd += ":"+old_pl_libs
        cmd += "\n"
    elif undercsh:
        tmp = "setenv PAPIEX_OPTIONS $PAPIEX_OPTIONS; setenv LD_PRELOAD $PAPIEX_LD_PRELOAD;"
        tmp += "setenv PAPIEX_OUTPUT $PAPIEX_OUTPUT;"
        if monitor_debug: tmp += "setenv MONITOR_DEBUG $MONITOR_DEBUG;"
        if papiex_debug: tmp += "setenv PAPIEX_DEBUG $PAPIEX_DEBUG;" 
        cmd += "alias epmt_instrument '"+tmp+"';\n"
#        cmd += "alias epmt 'epmt_uninstrument; ( command epmt \!* ); epmt_instrument;';\n"  
        cmd += "alias epmt_uninstrument 'unsetenv MONITOR_DEBUG PAPIEX_OUTPUT PAPIEX_DEBUG PAPIEX_OPTIONS"
        if not old_pl_libs:
            cmd += " LD_PRELOAD';"
        else:
            cmd += "';\nsetenv LD_PRELOAD $PAPIEX_OLD_LD_PRELOAD;"
        # CSH won't let an alias used in eval be used in the same eval, so we repeat this
        cmd +="\n"+tmp+"\n"
    elif not run_cmd:
# set up functions
        cmd += "epmt_push_preload ()\n{\nif [ -z \"$PAPIEX_OLD_LD_PRELOAD\" ]; then export LD_PRELOAD=$PAPIEX_LD_PRELOAD ; else export LD_PRELOAD=$PAPIEX_LD_PRELOAD:$PAPIEX_OLD_LD_PRELOAD ; fi\n};\n"
        cmd += "epmt_pop_preload ()\n{\nif [ -z \"$PAPIEX_OLD_LD_PRELOAD\" ]; then export -n LD_PRELOAD ; else export LD_PRELOAD=$PAPIEX_OLD_LD_PRELOAD ; fi\n};\n"
        cmd += "epmt_instrument () {\nexport MONITOR_DEBUG PAPIEX_OUTPUT PAPIEX_DEBUG PAPIEX_OPTIONS LD_PRELOAD;\n"
        cmd += "epmt_push_preload;\n};\n"
        cmd += "epmt_uninstrument () {\nexport -n MONITOR_DEBUG PAPIEX_OUTPUT PAPIEX_DEBUG PAPIEX_OPTIONS;\n"
        cmd += "epmt_pop_preload;\n};\n"
        #        cmd += "epmt () {\nepmt_pop_preload;\n cmd=`command epmt`;\nif [ $? -eq 0 ]; then $cmd $* ; else \"epmt not in \$PATH\"; fi\n;epmt_push_preload;\n};\n"
        # Now enable instrumentation
        cmd +="epmt_instrument;\n"
    return cmd

@logfn
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
        if dry_run:
            print("epmt start")
        else:
            if not epmt_start_job(keep_going=False):
                return 1

    logger.info("Executing(%s)",cmd)
    if not dry_run:
        #        return_code = forkexecwait(cmd, shell=True)
        return_code = run(cmd,shell=True).returncode
        logger.info("Exit code %d",return_code)
    else:
        print(cmd)
        return_code = 0

    if wrapit:
        if dry_run:
            print("epmt stop")
        else:
            if (epmt_stop_job(keep_going=False) == False):
                logger.warning("stop failed, but execution completed - data is likely corrupt")
    return return_code

def get_filedict(dirname,pattern,tar=False):
    logger.debug("get_filedict(%s,%s,tar=%s)",dirname,pattern,str(tar))
    # Now get all the files in the dir
    if tar:
        files = fnmatch.filter(tar.getnames(), pattern)
    else:
        files = glob(dirname+pattern)

    # TODO: Remove this gross hack
    files = [ f for f in files if not "papiex-header" in f ]

    if not files:
        logger.info("%s matched no files",pattern)
        return {}

    logger.info("%d files to submit: %s",len(files), str(files))
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
        # for csv v2 files we will end with a trailing hyphen, so remove it
        if host.endswith('-'):
            host = host[:-1]
        if filedict.get(host):
            filedict[host].append(f)
        else:
            filedict[host] = [ f ]
    if dumperr:
        logger.warn("Host not found in name split, using unknown host")

    return filedict

# if remove_on_success is set, on successful ingest the .tgz or job dir will be deleted
# if move_on_failure is set, on failed ingested, the .tgz or dir is moved away
# if keep_going is set, exceptions will not be raised
# if dry_run is set, don't touch the DB
# if drop is set, well just don't do that

def epmt_submit(dirs, ncpus = 1, dry_run=True, drop=False, keep_going=False, remove_on_success=False, move_on_failure=False):
    logger.debug("epmt_submit(%s,dry_run=%s,drop=%s,keep_going=%s,ncpus=%d,remove_on_success=%s,move_on_failure=%s)",dirs,dry_run,drop,keep_going,ncpus,remove_on_success,move_on_failure)

    # ARG checking
    
    if dry_run and drop:
        logger.error("You can't drop tables and do a dry run")
        return(False)
    from epmt.orm import orm_db_provider
    if (ncpus > 1) and ((settings.orm != 'sqlalchemy') or (orm_db_provider() != "postgres")):
        logger.error('Parallel submit is only supported for Postgres + SQLAlchemy at present')
        return False
    if not dirs:
        global_jobid,global_datadir,global_metadatafile = setup_vars()
        if not (global_jobid and global_datadir and global_metadatafile):
            logger.error("none should be null: global_job_id %s, global_data_dir %s, global_metdadatafile %s",
                         global_jobid,global_datadir,global_metadatafile);
            return False
        dirs  = [global_datadir]
    if not dirs or len(dirs) < 1:
        logger.error("directory for ingest is empty")
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
        logger.error('Dropping tables in a parallel submit mode, not supported')
        return(False)
        
    if drop:
        from epmt.orm import orm_drop_db, setup_db
        setup_db(settings)
        orm_drop_db()

    import multiprocessing

    def submit_fn(tid, work_list, ret_dict):
        logger.debug('Worker %d, PID %d', tid, getpid())
        retval = {}
        for f in work_list:
            r = submit_dir_or_tgz_to_db(f, pattern=settings.input_pattern, dry_run=dry_run, keep_going=keep_going, remove_on_success=remove_on_success, destdir_on_failure=move_on_failure if not move_on_failure else settings.ingest_failed_dir)
            logger.debug('post submit_dir_or_tgz_to_db()')
            # r = submit_to_db(f,settings.input_pattern,dry_run=dry_run, remove_on_success=remove_on_success)
            retval[f] = r
            (status, _, submit_details) = r
            if not keep_going:
                if not(status): 
                    break # there was an error
                # even if status is True, there is one condition
                # where the job is in the database, when we don't
                # have any submit_details. In such a case with keep_going
                # disabled, we need to error out
                if not(submit_details):
                    break
        # stringify the return values
        ret_dict[tid] = dumps(retval)
        logger.debug('submit_fn(): about to return')
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
        logger.debug('post-submit_fn()')
    else:
        logger.info('Using %d worker processes', nprocs)
        from numpy import array_split
        procs = []
        manager = multiprocessing.Manager()
        return_dict = manager.dict()
        for work in array_split(dirs, nprocs):
            logger.debug('Worker %d will work on directory %s', worker_id, str(work))
            process = multiprocessing.Process(target = submit_fn, args=(worker_id, work, return_dict))
            logger.debug('MP: post-submit_fn()')
            procs.append(process)
            worker_id += 1
        for p in procs:
            p.start()
        for p in procs:
            p.join()
    fini_ts = time.time()
    logger.info('Import done, preparing summary')
    # return_dict contains stringified return values to de-stringify them
    r = { k: loads(return_dict[k]) for k, v in return_dict.items() }
    total_procs = 0
    jobs_imported = []
    logger.info('**** Import Summary ****')
    error_occurred = False
    for v in r.values():
        for (f, res) in v.items():
            (status, msg, submit_details) = res
            if not status:
                logger.error('Error during import of %s: %s', f, res[1])
                error_occurred = True
            elif not submit_details:
                # we may have a True status, but if submit_details is empty
                # that means the job was already in the database, and we
                # couldn't submit it. Our behavior depends on whether keep_going
                # is enabled or not. If it is, then 
                logger.info('%s: %s', msg, f)
                if not keep_going:
                    error_occurred = True
            else:
                # status => True, and details contains the submit details
                (jobid, process_count) = submit_details
                jobs_imported.append(jobid)
                total_procs += process_count
    logger.info('Imported %d jobs (%d processes) in %2.2f sec at %2.2f procs/sec, %d workers', len(jobs_imported), total_procs, (fini_ts - start_ts), total_procs/(fini_ts - start_ts), nprocs)
    return(False if error_occurred else r)


@logfn
def copy_files(src_dir, dest_dir = '', patterns = ['*'], prefix = ''):
    '''
    Copy some or all files from one directory to another

    Parameters
    ----------
       src_dir : string
                 The directory to copy from
      dest_dir : string, optional
                 The destination directory. If unset,
                 one will be created using mkdtemp. If specified,
                 a directory will be created if it does not exist.
        prefix : This option is only meaningful if `dest_dir` is
                 not spcified, and mkdtemp is used to create a 
                 temporary directory. In that case, the prefix if
                 set will be honored while creating `dest_dir` name.
      patterns : list, optional
                 List of patterns to glob (relative to the `src_dir`)
                 If unset, all files in from_dir will be copied
    Returns
    -------
    Dest. directory on success, False on error

    Notes
    -----
    This function does not support recursive copying at present.
    If `dest_dir` is not specified, and the copy operation fails,
    then the temporary directory created by this function will be
    removed before it returns.
    '''
    if not path.isdir(src_dir):
        logger.error('%s does not exist', src_dir)
        return False

    created_tempdir = False # set true if we create a temp dir
    if dest_dir:
        try:
            mkdir(dest_dir)
        except FileExistsError:
            # directory exists. Good, that's what we need.
            pass
        except OSError as e:
            logger.error('mkdir(%s) failed: %s', dest_dir, str(e))
    else:
        # make a temp dir
        from tempfile import mkdtemp, gettempdir
        dest_dir = mkdtemp(prefix= prefix or 'epmt_stage_',dir=gettempdir())
        created_tempdir = True # so we can remember to remove it if needed

    # get all the matching paths
    matching_paths = []
    for p in patterns:
        matching_paths.extend(glob(src_dir + '/' + p))

    files = [ f for f in matching_paths if path.isfile(f) ] 

    if not files:
        logger.debug('No files to copy!')
        return False
    logger.debug('Copying {} to {}'.format(files, dest_dir))
    for f in files:
        filename = path.basename(f)
        target = dest_dir + "/" + filename
        try:
            copyfile(f, target)
        except Exception as e:
            logger.error("copyfile(%s,%s): %s",f,target,str(e))
            # if we created a tempdir, then we better cleanup
            if created_tempdir:
                rmtree(dest_dir, ignore_errors=True)
            return False

    # If we reached here, we were successful in copying the
    # requested files
    return dest_dir


def create_tar(tarfile, indir, remove_dir = False):
    '''
    Create a tar file

        Parmeters
        ---------
          tarfile : string
                    Path to output tar file. If it exists it will
                    be silently overwritten
            indir : The directory whose contents will be tarred
       remove_dir : If enabled, `indir` will be removed after
                    completion of the tar operation regardless
                    of the status of the tar operation itself

    Returns
    -------
    True on success, False on error
    '''
    if not path.isdir(indir):
        logger.error('{} does not exist'.format(indir))
    cmd = "tar -C "+indir+" -cz -f "+tarfile+" ."
    logger.debug(cmd)
    retval = run(cmd, shell=True).returncode
    if retval != 0:
        logger.error('%s failed', cmd)
    if remove_dir:
        try:
            rmtree(indir)
        except OSError as e:
            logger.warning('rmtree(%s) failed: %s', indir, str(e))
    return (retval == 0)


def extract_tar(tarfile, outdir = '', check_metadata = False):
    '''
    Extract staged .tgz file

    Parameters
    ----------
        tarfile : string
                  Path to tarfile
         outdir : string, optional
                  Directory to extract to. If unset, a temporary
                  directory will be created using mkdtemp
 check_metadata : boolean, optional
                  If set, the tar will be searched for a job
                  metadata file, and if not found an error will
                  be returned. Default is False, which means
                  no check for metadata file will be performed.

    Returns
    -------
    Output directory where tar was extracted on success,
    False on error

    '''
    if not path.isfile(tarfile):
        logger.error("%s does not exist!", tarfile)
        return False
    err,tar = open_compressed_tar(tarfile)

    # only check for metadata file if required to do so
    if check_metadata:
        try:
            info = tar.getmember("./job_metadata")
        except KeyError:
            logger.error('ERROR: Did not find %s in tar file' % "job_metadata")
            return False
        logger.info('%s is %d bytes in archive' % (info.name, info.size))

    from tempfile import mkdtemp, gettempdir
    outdir = outdir or mkdtemp(prefix='epmt_stage_',dir=gettempdir())
    logger.debug('extracting {0} to {1}'.format(tarfile, outdir))
    try:
        tar.extractall(path=outdir)
    except Exception as e:
        logger.error('Error extracting {} into {}: {}'.format(tarfile, outdir, str(e)))
        # cleanup since we had an error
        rmtree(outdir, ignore_errors=True)
        return False
    return outdir


def open_compressed_tar(inputf):
    tar = None
    flags = None
    if (inputf.endswith("tar.gz") or inputf.endswith("tgz")):
        flags = "r:gz"
    elif (inputf.endswith("tar")):
        flags = "r:"
    else:
        return False,None
    
    import tarfile
    try:
        tar = tarfile.open(inputf, flags)
    except Exception as e:
        logger.error('error opening compressed tar ' + inputf + ":" + str(e))
        return True,None
    
    return False,tar
    
# Compute differences in environment if detected
# Merge start and stop environments
#    total_env = start_env.copy()
#    total_env.update(stop_env)
# Check for Experiment related variables
#    metadata = check_and_add_workflowdb_envvars(metadata,total_env)

# remove_on_success is set, then we will delete the file on success
def submit_dir_or_tgz_to_db(inputf, pattern=settings.input_pattern, dry_run=True, keep_going=False, remove_on_success=settings.ingest_remove_on_success, destdir_on_failure=settings.ingest_failed_dir):
    def move_away(from_file,to_dir):
        if to_dir:
            logger.info("move(%s,%s)",from_file,to_dir)
            try:
                move(from_file,to_dir)
            except Exception as e:
                logger.error("Exception from move(%s,%s): %s",from_file,to_dir,str(e))
            logger.info("done: move(%s,%s)",from_file,to_dir)
        
    def trash(from_path):
        logger.info("sending %s to trash",from_path);
        try:
            if path.isfile(from_path):
                remove(from_path)
            elif path.isdir(from_path):
                rmtree(from_path, ignore_errors=True)
        except Exception as e:
            logger.error("Exception from remove/rmtree(%s): %s",from_path,str(e))

    def goodpath(from_path):
        return (path.isfile(from_path) and (from_path.endswith("tar.gz") or from_path.endswith("tgz") or from_path.endswith("tar"))) or path.isdir(from_path) 
    
    if not goodpath(inputf):
        return (False, "submit_dir_or_tgz_to_db("+inputf+") not a job dir or tar archive", ())

    status = False
    exc = None
    r = None
    msg = "submit_dir_or_tgz_to_db({}): ".format(inputf) 
    
    try:
        r = submit_to_db(inputf,pattern,dry_run=dry_run)
    except Exception as e:
        msg += str(e)
        exc = e
        if not keep_going:
            exc.args = (msg, *exc.args)
            move_away(inputf,destdir_on_failure)
            raise exc
        
    if not r:
        r = (False, msg, ())
    (status, msg, submit_details) = r

    if not status:
        logger.debug("Status is False")
        move_away(inputf,destdir_on_failure)
    elif remove_on_success:
        trash(inputf)

    return r

def submit_to_db(inputf, pattern, dry_run=True):
    logger.info("submit_to_db(%s,%s,dry_run=%s)",inputf,pattern,str(dry_run))

    err,tar = open_compressed_tar(inputf)
    if err:
        return (False, 'Error processing compressed tar file '+inputf, ())
#    None
#    if (input.endswith("tar.gz") or input.endswith("tgz")):
#        import tarfile
#        tar = tarfile.open(input, "r:gz")
#    elif (input.endswith("tar")):
#        import tarfile
#        tar = tarfile.open(input, "r:")
    if not tar and not inputf.endswith("/"):
        logger.warning("missing trailing / on submit dirname %s",inputf);
        inputf += "/"

    if tar:
#        for member in tar.getmembers():
        try:
            info = tar.getmember("./job_metadata")
        except KeyError:
            logger.error('Did not find %s in tar file %s' % ("job_metadata",inputf))
            return (False, 'Did not find metadata in tar file '+inputf, ())
        else:
            logger.info('%s is %d bytes in tar file %s' % (info.name, info.size, inputf))
            f = tar.extractfile(info)
            metadata = read_job_metadata_direct(f)
            filedict = get_filedict(None,settings.input_pattern,tar)
    else:
        metadata = read_job_metadata(inputf+"job_metadata")
        filedict = get_filedict(inputf,settings.input_pattern)

    if not metadata:
        return (False, 'missing job metadata', ())

    logger.info("%d hosts found: %s",len(filedict.keys()),filedict.keys())
    for h in filedict.keys():
        logger.info("host %s: %d files to import",h,len(filedict[h]))

# Do as much as we can before bailing
    if dry_run:
#        check_workflowdb_dict(metadata,pfx="exp_")
        logger.info("Dry run finished, skipping DB work")
        # the third parameter below, represents the submit details
        # It's empty because we didn't actually submit anything
        return (True, 'Dry run finished, skipping DB work', ())

# Now we touch the Database
    from epmt.orm import setup_db
    if setup_db(settings,False) == False:
        return (False, 'Error in DB setup', ())
    from epmt.epmt_job import ETL_job_dict
    r = ETL_job_dict(metadata,filedict,settings,tarfile=tar)
    return r
    # (j, process_count) = r[-1]
    # logger.info("Committed job %s to database: %s",j.jobid,j)
    # return (j.jobid, process_count)

@logfn
def stage_job(indir,collate=True,compress_and_tar=True,keep_going=True):
    if not indir or len(indir) == 0:
        logger.error("stage_job: indir is epmty")
        return False
    if not settings.stage_command or not settings.stage_command_dest or len(settings.stage_command) == 0 or len(settings.stage_command_dest) == 0: 
        logger.debug("stage_job: no stage commands to do")
        return True
    import time
    _start_staging_time = time.time()
    # Always collate into local temp dir
    if collate:
        tempdir = copy_files(indir, patterns = ['job_metadata'], prefix = 'epmt_stage_')
        if not tempdir:
            logger.error("No job metadata found in " + indir)
            # no need to cleanup as copy_files will clean 
            # up temp dir if it created one using mkdtemp
            return False
        tsv_files = glob(indir + '/*.tsv')
        if (tsv_files):
            copied_to = copy_files(indir, dest_dir = tempdir, patterns = ['*.tsv'])
            if not copied_to:
                logger.error('No job performance data found in {}'.format(indir))
                rmtree(tempdir, ignore_errors=True)
                return False
        else:
            # the old csv 1.0 concatenation using csvjoiner
            from epmt.epmt_concat import csvjoiner
            status, _, badfiles = csvjoiner(indir, outpath=tempdir+"/", keep_going=keep_going, errdir=settings.error_dest)
            if status == False:
                logger.debug("csv concatenation returned status = %s",status)
                rmtree(tempdir, ignore_errors=True)
                return False
            if badfiles:
                d={}
                d["epmt_stage_error"]=str(badfiles)
                logger.error("Job being annotated with %s",str(d))
                # begin HACK: should call a real annotate function            
                metadatafile = tempdir+"/job_metadata"
                metadata = read_job_metadata(metadatafile)
                if not metadata:
                    logger.error("Failed to get %s for annotation of erroneous stage",metadatafile)
                    rmtree(tempdir, ignore_errors=True)
                    return False
                if not annotate_metadata(metadatafile,d,replace=False):
                    logger.error("Failed to write to %s annotations of erroneous stage",metadatafile)
                    rmtree(tempdir, ignore_errors=True)
                    return False
                
        from tempfile import gettempdir
        if compress_and_tar:
            filetostage = gettempdir()+"/"+path.basename(path.dirname(indir))+".tgz"
            # create tar, and bail on error
            if not create_tar(filetostage, tempdir, remove_dir = True):
                return False
        else:
            filetostage = gettempdir()+"/"+path.basename(path.dirname(indir))
            move(tempdir,filetostage)
            
# end HACK
    cmd = settings.stage_command + " " + filetostage + " " + settings.stage_command_dest
    logger.info(cmd)
    return_code = run(cmd, shell=True).returncode
    if path.exists(filetostage):
        try:
            logger.debug("rmtree(%s)",filetostage)
            rmtree(filetostage)
        except Exception as e:
            logger.debug("rmtree(%s): %s",filetostage,str(e))
    logger.debug('staging took: %2.5f sec', time.time() - _start_staging_time)
    if return_code == 0:
        print(path.normpath(settings.stage_command_dest)+"/"+path.basename(filetostage))
        try:
            logger.info("rmtree(%s)",indir)
            rmtree(indir)
        except Exception as e:
            logger.warning("rmtree(%s): %s",indir,str(e))
        return True
    return False

@logfn
def epmt_stage(dirs, keep_going=True, collate=True, compress_and_tar=True):
    if not dirs:
        global_jobid,global_datadir,global_metadatafile = setup_vars()
        if not (global_jobid and global_datadir and global_metadatafile):
            return False
        dirs  = [global_datadir]

    logger.debug("staging %s",dirs)
    r = True
    for d in dirs:
        if not d.endswith("/"):
            logger.warning("missing trailing / on %s",d)
            d += "/"
        r = stage_job(d,collate=collate,compress_and_tar=compress_and_tar,keep_going=keep_going)
        if r is False and not keep_going:
            logger.debug("stage_job early exit status = %s",r)
            return False

    logger.debug("stage_job final status = %s",r)    
    return r

def epmt_dbsize(findwhat=['database','table','index','tablespace'], usejson=True, usebytes=True):
    from epmt.orm import orm_db_size
# Absolutely all argument checking should go here, specifically the findwhat stuff
    if findwhat == "all":
        findwhat = ['database','table','index','tablespace']
    return(orm_db_size(findwhat,usejson,usebytes))

# Start a shell. if ipython is True (default) start a powerful
# ipython shell, otherwise a vanilla python shell
def epmt_shell(ipython = True):
    # we import builtins so pyinstaller will use the full builtins module
    # instead of a sketchy replacement. Also we need help from pydoc
    # since the builtins module included by pydoc doesn't have help
    import builtins
    from pydoc import help
    kwargs = {}
    try:
        # locals() gives an exception if run in the epmt
        # directory created by pyinstaller. It works elsewhere
        # So it will run in the user directories fine. However,
        # out integration tests run from the 'epmt' directory
        # and may fail. So, just handle the exception and pass
        # an empty local namespace if necessary
        args = { 'local': locals() }
    except:
        pass
    if ipython:
        # ipython shell
        from IPython import embed
        embed(**kwargs)
    else:
        # regular python shell
        from code import interact
        interact(**kwargs)


def epmt_entrypoint(args):

    # I hate this sequence.

    if args.verbose == None:
        args.verbose = 0
    # we only need to log the PID to the console for parallel runs
    epmt_logging_init(args.verbose or settings.verbose, check=True, log_pid = (hasattr(args, 'num_cpus') and (args.num_cpus > 1)))
    logger = getLogger(__name__)  # you can use other name
    init_settings(settings)

    # Here it's up to each command to validate what it is looking for
    # and error out appropriately
    if args.command == 'shell':
        epmt_shell()
        return 0
    if args.command == 'python':
        script_file = args.epmt_cmd_args
        if script_file:
            if script_file == '-':
                # special handling for stdin
                from sys import stdin
                f = stdin
            else:
                if not path.exists(script_file):
                    logger.error('script {} does not exist'.format(script_file))
                    return(-1)
                else:
                    f = open(script_file)
            # Pony needs the session with a db_session context manager
            # SQLA doesn't care. We also don't have the SQLA db_session
            # honoring the context manager contract yet. So, we have
            # to have some conditional code unfortunately
            #if settings.orm == 'pony':
            #    with db_session:
            #        exec(f.read())
            #else:
            exec(f.read())
        else:
            epmt_shell(ipython = False)
        return 0
    if args.command == 'convert':
        from epmt.epmt_convert_csv import convert_csv_in_tar
        return (convert_csv_in_tar(args.src_tgz, args.dest_tgz) == False)
    if args.command == 'explore':
        from epmt.epmt_exp_explore import exp_explore
        exp_explore(args.epmt_cmd_args, metric = args.metric, limit = args.limit)
        return 0
    if args.command == 'gui':
        # Start both Dash interface and Static Web Server
        from threading import Thread
        from epmt.ui import init_app, app
        from serve_static import app as docsapp
        # Bug in pyinstaller does not import the idna encoding
        import encodings.idna
        # Here app is the content of the dash interface
        init_app()
        ui = Thread(target=app.run_server, kwargs={'port':8050, 'host':'0.0.0.0'})
        docs = Thread(target=docsapp.run, kwargs={'port':8080, 'host':'0.0.0.0'})
        ui.start()
        docs.start()
        return 0

    if args.command == 'integration':
        import subprocess
        from epmt.epmtlib import get_install_root
        from glob import glob
        req_tests = None
        tests_to_run = []
        logger.debug("exclude {}".format(args.exclude))
        if args.epmt_cmd_args:
            req_tests = args.epmt_cmd_args
        install_root = get_install_root()
        bats_tester = install_root+'/test/integration/libs/bats/bin/bats'
        #sample_test = install_root+'/test/integration/001-basic.bats'
        test_folder = install_root+'/test/integration'
        logger.debug("Bats: {}".format(bats_tester))
        logger.debug("test directory: {}".format(test_folder))
        from glob import glob
        from os.path import basename
        # Get test names in test directory
        tests = sorted([basename(x) for x in glob(test_folder+'/*.bats')])
        # Search the requested test names without path for a match
        if req_tests:
            for r in req_tests:
                added = False
                for t in tests:
                    # if test is requested
                    if r in t:
                        tests_to_run.append(t)
                        added = True
                if not added:
                    logger.warning("Could not find a test containing '{}' in testdir: {}".format(r,test_folder))
        else:
            tests_to_run = tests
        
        #tests_to_run = ' '.join([test_folder + '/' + t if x not in t else '' for x in args.exclude for t in tests_to_run])
        good_tests = []
        if len(args.exclude)>0:
            for t in tests_to_run:
                    for x in args.exclude:
                        if x not in t:
                            good_tests.append(test_folder + '/' + t)
        else:
            for t in tests_to_run:
                good_tests.append(test_folder + '/' + t)
        good_tests = ' '.join(good_tests)
        logger.debug("Tests to run {}".format(good_tests))
        if len(good_tests) < 1:
                from sys import stderr
                print('No test found', file=stderr)
                return -1
        cmd = bats_tester+" "+good_tests
        logger.debug(cmd)
        # set up a signal handler so we can make sure we trap common
        # interrupts and also send the SIGTERM to spanwed child processes
        from epmt.epmtlib import set_signal_handlers
        from signal import SIGTERM
        import psutil
        from sys import stderr
        def sig_handler(signo, frame):
            print("Sending TERM to child processes..", file=stderr)
            # use psutil to determine all the child processes
            current_process = psutil.Process()
            children = current_process.children(recursive=True)
            for child in children:
                kill(child.pid, SIGTERM)
        set_signal_handlers([], sig_handler)
        retval = subprocess.run(cmd, shell=True)
        # restore signal handlers to the defaults
        set_signal_handlers([])
        return retval.returncode

    if args.command == 'unittest':
        import unittest
        from importlib import import_module
#        script_dir = path.dirname(path.realpath(__file__))
#        logger.info("Changing directory to: {}".format(script_dir))
#        chdir(script_dir)
        TEST_MODULES = ['test.test_lib','test.test_settings','test.test_anysh','test.test_submit','test.test_run','test.test_cmds','test.test_query','test.test_outliers','test.test_db_schema' ]
        if args.epmt_cmd_args:
            TEST_MODULES = args.epmt_cmd_args
        success_list=[]
        print(f'\n\nverbosity for tests set by epmt_logging_init')
        for m in TEST_MODULES:
            # i could import test in epmt shell, but not epmt.test
            m = f'epmt.{m}'
            # comment-out line above for use in epmt shell
            mod = import_module(m)
            suite = unittest.TestLoader().loadTestsFromModule(mod)
            print('\n\nRunning', m)
            result = unittest.TextTestRunner(verbosity=2).run(suite)
            success_list.append(result.wasSuccessful())
            if not result.wasSuccessful():
                from sys import stderr
                print('\n\nOne (or more) unit tests FAILED', file=stderr)
                #return -1
            if not any(success_list):
                return -1
        print('All tests successfully PASSED')
        return 0

    if args.command == 'retire':
        from epmt.epmt_cmd_retire import epmt_retire
        epmt_retire(skip_unprocessed=args.skip_unproc, dry_run=args.dry_run)
        return 0

    if args.command == 'check':
        # fake a job id so that epmt_check doesn't fail because of a missing job id
        environ['SLURM_JOB_ID'] = '1'
        return(0 if epmt_check() else 1)

    if args.command == 'daemon':
        from epmt.epmt_daemon import start_daemon, stop_daemon, daemon_loop, print_daemon_status
        if args.no_analyze and not args.post_process:
            logger.error("Skipping analysis requires post processing to be enabled")
            return 0
                         
        if args.start or args.foreground:
            if not args.ingest and not args.post_process and not args.retire:
                # if no command is set, default to post-process and analyze
                logger.warning('No daemon mode set, defaulting to post-process and analysis')
                args.post_process = True
                args.no_analyze = False
            daemon_args = { 'post_process': args.post_process, 'analyze': not args.no_analyze, 'ingest': args.ingest, 'recursive': args.recursive, 'keep': args.keep, 'move_away': args.move_away, 'retire': args.retire, 'verbose': args.verbose }
            return start_daemon(args.foreground,**daemon_args)
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
        from epmt.orm import orm_drop_db
        orm_drop_db()
        return 0
    if args.command == 'dbsize':
        return(epmt_dbsize(args.epmt_cmd_args) == False)
    if args.command == 'start':
        return(epmt_start_job(keep_going=not args.error, other=args.epmt_cmd_args) == False)
    if args.command == 'stop':
        return(epmt_stop_job(keep_going=not args.error, other=args.epmt_cmd_args) == False)
    if args.command == "stage":
        return(epmt_stage(args.epmt_cmd_args,keep_going=not args.error,collate=not args.no_collate,compress_and_tar=not args.no_compress_and_tar) == False)
    if args.command == 'run':
        return(epmt_run(args.epmt_cmd_args,wrapit=args.auto,dry_run=args.dry_run,debug=(args.verbose > 2)))
    if args.command == 'annotate':
        return(epmt_annotate(args.epmt_cmd_args, args.replace) == False)

    if args.command == 'schema':
        from epmt.orm import orm_dump_schema
        return (orm_dump_schema() == False)

    if args.command == 'migrate':
        from epmt.orm import setup_db
        return (setup_db(settings) == False)

    # show functionality is now handled in the 'dump' command
    # if args.command == 'show':
    #     from epmt.epmt_cmd_show import epmt_show_job
    #     return(epmt_show_job(args.epmt_cmd_args, key = args.key) == False)
    if args.command == 'source':
        s = epmt_source(slurm_prolog=args.slurm,papiex_debug=(args.verbose > 2),monitor_debug=(args.verbose > 3))
        if not s:
            return(1)
        print(s,end="")
        return(0)
    if args.command == 'dump':
        return(epmt_dump_metadata(args.epmt_cmd_args, key = args.key) == False)
    if args.command == 'submit':
        return(epmt_submit(args.epmt_cmd_args,dry_run=args.dry_run,drop=args.drop,keep_going=not args.error, ncpus = args.num_cpus, remove_on_success=args.remove, move_on_failure=args.move_away) == False)
    if args.command == 'check':
        return(epmt_check() == False)
    if args.command == 'delete':
        from epmt.epmt_cmd_delete import epmt_delete_jobs
        return(epmt_delete_jobs(args.epmt_cmd_args) == False)
    if args.command == 'list':
        from epmt.epmt_cmd_list import epmt_list
        return(epmt_list(args.epmt_cmd_args) == False)
    if args.command == 'notebook':
        from epmt.epmt_cmd_notebook import epmt_notebook
        return(epmt_notebook(args.epmt_cmd_args) == False)

    logger.error("Unknown command, %s. See -h for options.",args.command)
    return(1)
