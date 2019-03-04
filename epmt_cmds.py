#!/usr/bin/env python
from logging import getLogger, basicConfig, DEBUG, INFO, WARNING, ERROR
from datetime import datetime
from os import environ, makedirs, errno, path, getpid, getuid, getsid
from socket import gethostname
#from json import dumps as dict_to_json
from subprocess import call as forkexecwait
from random import randint
from imp import find_module
from grp import getgrall, getgrgid
from pwd import getpwnam, getpwuid
from glob import glob
from sys import stdout, stderr
import fnmatch
import pickle

import settings
for k in [ "provider", "user", "password", "host", "dbname", "filename" ]:
    t = environ.get("EPMT_DB_"+ k.upper())
    if t:
        settings.db_params[k] = t

def getgroups(user):
    gids = [g.gr_gid for g in getgrall() if user in g.gr_mem]
    logger.debug("Group ids: %s",str(gids))
    gid = getpwnam(user).pw_gid
    logger.debug("My id: %s",gid)
    if gid not in gids:
        gids.append(getgrgid(gid).gr_gid)
    return [getgrgid(gid).gr_name for gid in gids]

# Done later
#from dictdiffer import diff

logger = getLogger(__name__)  # you can use other name

#
#
# Torque
# http://docs.adaptivecomputing.com/torque/4-1-7/Content/topics/2-jobs/exportedBatchEnvVar.htm
key2pbs = {
	"JOB_ACCOUNT":"PBS_ACCOUNT",
	"JOB_HOST":"PBS_O_HOST",
	"JOB_ID":"PBS_JOBID",
	"JOB_INDEX_ON_NODE":"PBS_O_VNODENUM",
	"JOB_NAME":"PBS_JOBNAME",
	"JOB_NODEFILE":"PBS_NODEFILE",
	"JOB_NODE_MAX":"PBS_NUM_NODES",
	"JOB_NODE_RANK":"PBS_NODENUM",
	"JOB_PATH_ENV":"PBS_O_PATH",
	"JOB_QUEUE_NAME":"PBS_QUEUE",
	"JOB_SHELL":"PBS_O_SHELL",
	"JOB_RANK":"PBS_ARRAYID",
	"JOB_RANK_MAX":"PBS_TASKNUM",
	"JOB_USER":"PBS_O_LOGNAME",
	"JOB_USER_HOME":"PBS_O_HOME",
	"JOB_WORKDIR":"PBS_O_WORKDIR"
	}
# Slurm
# http://hpcc.umd.edu/hpcc/help/slurmenv.html
key2slurm = {
	"JOB_ACCOUNT":"SLURM_JOB_ACCOUNT",
	"JOB_HOST":"SLURM_SUBMIT_HOST",
	"JOB_ID":"SLURM_JOBID",
	"JOB_INDEX_ON_NODE":"SLURM_LOCALID",
	"JOB_MACHINE":"SLURM_CLUSTER_NAME", 
	"JOB_NODE_MAX":"SLURM_JOB_NODES",
	"JOB_RANK_MAX":"SLURM_NTASKS",
	"JOB_NAME":"SLURM_JOB_NAME", 
	"JOB_NODELIST":"SLURM_JOB_NODELIST",
	"JOB_NODE_RANK":"SLURM_NODEID",
	"JOB_PARTITION":"SLURM_JOB_PARTITION",
	"JOB_RANK":"SLURM_PROCID",
	"JOB_WORKDIR":"SLURM_SUBMIT_DIR"
}
#	"JOB_ID":"SLURM_JOB_ID",
#	"JOB_MAXRANK":"SLURM_NPROCS",

global_job_id = ""
global_job_name = ""
global_job_scriptname = ""
global_job_username = ""
global_job_groupnames = ""

def set_job_globals(cmdline=[]):
	global global_job_id, global_job_name, global_job_scriptname
	global global_job_username, global_job_groupnames

	global_job_id = get_job_var("JOB_ID")
	if not global_job_id:
		global_job_id=str(getsid(0))
		logger.warn("JOB_ID unset: Using session id %s as JOB_ID",global_job_id)

	global_job_name = get_job_var("JOB_NAME")
	if not global_job_name:
		if cmdline:
			global_job_name=' '.join(cmdline)
			logger.warn("JOB_NAME unset: Using command line %s as JOB_NAME",global_job_name)
		else:
			global_job_name=global_job_id
			logger.warn("JOB_NAME unset: Using job id %s as JOB_NAME",global_job_name)

	global_job_scriptname = get_job_var("JOB_SCRIPTNAME")
	if not global_job_scriptname:
		global_job_scriptname=global_job_name
		logger.warn("JOB_SCRIPTNAME unset: Using process name %s as JOB_SCRIPTNAME",global_job_name)

	global_job_username = get_job_var("JOB_USER")
	if not global_job_username:
		global_job_username = getpwuid(getuid()).pw_name
		logger.warn("JOB_USER unset: Using username %s as JOB_USER",global_job_username)

	global_job_groupnames = getgroups(global_job_username)
		
	logger.debug("ID: %s",global_job_id)
	logger.debug("NAME: %s",global_job_name)
	logger.debug("SCRIPTNAME: %s",global_job_scriptname)
	logger.debug("USER: %s",global_job_username)
	logger.debug("GROUPS: %s",global_job_groupnames)
	return global_job_id


# Remove those with _ at beginning
def blacklist_filter(filter=None, **env):
#	print env
	env2 = {}
	for k, v in env.iteritems():
		if not k.startswith("_"):
			env2[k] = v
	return env2

def get_job_var(var):
	logger.debug("looking for %s",var)
	a = False
	if var in key2pbs:
		logger.debug("looking for %s",key2pbs[var])
		a=environ.get(key2pbs[var])
	if not a and var in key2slurm:
		logger.debug("looking for %s",key2slurm[var])
		a=environ.get(key2slurm[var])
	if not a:
		logger.debug("%s not found",var)
		return False
	return a

def dump_config(outf):
    print >> outf,"\nsettings.py (overridden by below env. vars):"
#    book = {}
    for key, value in sorted(settings.__dict__.iteritems()):
        if not (key.startswith('__') or key.startswith('_')):
            print >> outf,"%-24s%-56s" % (key,str(value))
    print >> outf,"\nenvironment variables (overrides settings.py):"
    for v in [ "PAPIEX_OSS_PATH", "PAPIEX_OUTPUT"
# "PAPIEX_OPTIONS","PAPIEX_DEBUG","PAPI_DEBUG","MONITOR_DEBUG","LIBPFM_DEBUG"
              ]:
        if v in environ:
            print >> outf,"%-24s%-56s" % (v,environ[v])

def create_job_prolog(jobid, from_batch=[]):
	metadata = {}
	ts=datetime.now()
	env=blacklist_filter(filter,**environ)
#	print env
	metadata['job_pl_id'] = global_job_id
	metadata['job_pl_scriptname'] = global_job_scriptname
	metadata['job_pl_hostname'] = gethostname()
	metadata['job_pl_jobname'] = global_job_name
	metadata['job_pl_username'] = global_job_username
	metadata['job_pl_groupnames'] = global_job_groupnames
	metadata['job_pl_submit'] = datetime.now()
	metadata['job_pl_env_len'] = len(env)
	metadata['job_pl_env'] = env
	metadata['job_pl_start'] = ts
	metadata['job_pl_from_batch'] = from_batch

	return metadata

#
#       WorkflowDB detection
#

def check_workflowdb_dict(d,pfx=""):
    if all (k in d for k in (pfx+"name",pfx+"component",pfx+"oname",pfx+"jobname")):
        logger.info("*** Workflow detected*** job(%s,%s)",d["job_pl_id"], d["job_pl_jobname"]);
        logger.info("name(%s), component(%s), oname(%s) and jobname(%s)",d[pfx+"name"],d[pfx+"component"],d[pfx+"oname"],d[pfx+"jobname"])
        return True
    return False

def check_and_add_workflowdb_envvars(metadata, env):
    if check_workflowdb_dict(env):
        metadata["exp_name"] = env["name"]
        metadata["exp_component"] = env["component"]
        metadata["exp_oname"] = env["oname"]
        metadata["exp_jobname"] = env["jobname"]
    return metadata

def create_job_epilog(prolog, from_batch=[], status="0"):
    metadata={}
    env={}
    ts=datetime.now()
    stop_env=blacklist_filter(filter,**environ)
# Compute differences in environment if detected
    start_env=prolog['job_pl_env']
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
#        try:
#            find_module('dictdiffer')
#            import dictdiffer
#            env = list(dictdiffer.diff(prolog['job_pl_env'],env))
#        except ImportError:
#            logger.warn("dictdiffer module not found");
#            env = env
    metadata['job_el_env_changes_len'] = len(env)
    metadata['job_el_env_changes'] = env
    metadata['job_el_stop'] = ts
    metadata['job_el_from_batch'] = from_batch
    metadata['job_el_status'] = status
# Merge start and stop environments
    total_env = start_env.copy()
    total_env.update(stop_env)
# Check for Experiment related variables
    metadata = check_and_add_workflowdb_envvars(metadata,total_env)
    return metadata

def write_job_prolog(jobdatafile,data):
	with open(jobdatafile,'w+b') as file:
		pickle.dump(data,file)
		logger.debug("Pickled to "+jobdatafile)
		return True
	return False
	# collect env

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

# Clean files from tmp storage
def job_clean():
	return True

# Gather files from tmp storage to persistant storage
def job_gather():
	return True

def get_job_id():
	global global_job_id
	return(global_job_id)

def get_job_dir(hostname="", prefix=settings.papiex_output):
    if not prefix.endswith("/"):
        logger.warning("missing trailing / on prefix %s",prefix);
        prefix += "/"

    dirname = ""
    t = environ.get("PAPIEX_OUTPUT")
    if t and len(t) > 0:
        dirname = t
        if not dirname.endswith("/"):
            logger.warning("missing trailing / on PAPIEX_OUTPUT variable %s",dirname);
            dirname += "/"
    elif t:
        logger.error("PAPIEX_OUTPUT is set but blank")
        exit(1)
    else:
        if global_job_id == "":
            logger.warning("Unknown job id, trying to find it...")
            set_job_globals()
        dirname = prefix+global_job_id+"/"

    return dirname

def get_job_metadata_file(hostname="", prefix=settings.papiex_output):
	s = get_job_dir(hostname,prefix)
	return s+"job_metadata"

def create_job_dir(dir):
	try:
		makedirs(dir,0700) 
		logger.info("created dir %s",dir)
	except OSError as e:
		if e.errno != errno.EEXIST:
			logger.error("dir %s: %s",dir,e)
			return False
		logger.debug("dir exists %s",dir)
	return dir

#
#
#
#db.bind(**settings.db_params)
def epmt_start(from_batch=[]):
    jobid = get_job_id()
    dir = create_job_dir(get_job_dir())
    if dir is False:
        exit(1)
    file = get_job_metadata_file()
    if path.exists(file):
        logger.error("%s already exists!",file)
        exit(1)
    metadata = create_job_prolog(jobid,from_batch)
    write_job_prolog(file,metadata)
    logger.info("wrote prolog to %s",file);
    logger.debug("%s",metadata)
    return metadata

def epmt_dump_metadata_file(filelist):
    if len(filelist) == 0:
        set_job_globals()
        filelist = [get_job_metadata_file()]

    for file in filelist:
        if not path.exists(file):
            logger.error("%s does not exist!",file)
            exit(1)

        tar = compressed_tar(file)
        if tar:
            try:
                info = tar.getmember("job_metadata")
            except KeyError:
                logger.error('ERROR: Did not find %s in tar archive' % "job_metadata")
                exit(1)
            else:
                logger.info('%s is %d bytes in archive' % (info.name, info.size))
                f = tar.extractfile(info)
                metadata = read_job_metadata_direct(f)
        else:
            metadata = read_job_metadata(file)

        if not metadata:
            return False
        for d in sorted(metadata.keys()):
            print "%-24s%-56s" % (d,str(metadata[d]))
    return True

def epmt_stop(from_batch=[]):
	jobid = get_job_id()
	file = get_job_metadata_file()
	if file is False:
		exit(1)
	prolog = read_job_metadata(file)
	if not prolog:
		return False
	logger.info("read prolog from %s",file);
        if "job_el_stop" in prolog:
            logger.error("%s is already complete!",file)
            exit(1)
	epilog = create_job_epilog(prolog,from_batch)
	metadata = merge_two_dicts(prolog,epilog)
	write_job_epilog(file,metadata)
	logger.info("rewrote %s with prolog + epilog",file);
	logger.debug("%s",metadata)
	return metadata


def epmt_test_start_stop(from_batch=[]):
	d1 = epmt_start(from_batch)
	environ['INSERTED_ENV'] = "Yessir!"
	d2 = epmt_stop(from_batch)
 	d3 = merge_two_dicts(d1,d2)
 	d4 = read_job_metadata(jobdatafile=get_job_metadata_file())
 	print "Test is",(d3 == d4)
	if (d3 != d4):
		exit(1)
	print d4
	
def epmt_source(output_dir, options, papiex_debug=False, monitor_debug=False):
	t = environ.get("PAPIEX_OSS_PATH")
	if t and path.exists(t):
            logger.info("Overriding settings.install_prefix with PAPIEX_OSS_PATH=",t)
            dirname = t
        else:
            dirname = settings.install_prefix
        if not dirname.endswith("/"):
            logger.error("Warning missing trailing / on %s",dirname);
            dirname += "/"

	cmd = "PAPIEX_OPTIONS="+options
	if output_dir:
            cmd += " PAPIEX_OUTPUT="+output_dir
        if papiex_debug:
            cmd += " PAPIEX_DEBUG=TRUE"
        if monitor_debug:
            cmd += " MONITOR_DEBUG=TRUE"
	cmd += " LD_PRELOAD="+dirname+"lib/libpapiex.so:"+dirname+"lib/libmonitor.so"
        return cmd

def epmt_run(cmdline, wrapit=False, dry_run=False, debug=False):
	logger.debug(cmdline)

        if wrapit:
            logger.info("Forcing epmt_start")
            if dry_run:
                print "epmt start"
            else:
                epmt_start()

	cmd = epmt_source(get_job_dir(), settings.papiex_options, papiex_debug=debug, monitor_debug=debug)
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
                epmt_stop()

	return return_code

def get_filedict(dirname,pattern=settings.input_pattern,tar=False):
    # Now get all the files in the dir
    if tar:
        files = fnmatch.filter(tar.getnames(), pattern)
    else:
        files = glob(dirname+pattern)

    if not files:
        logger.warning("%s matched no files",dirname+pattern)
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

def epmt_submit_list(stuff, dry_run=True, drop=False):
    if dry_run and drop:
        logger.error("You can't drop tables and do a dry run")
        exit(1)
        
    if stuff:
        for f in stuff:
            submit_to_db(f,settings.input_pattern,dry_run=dry_run,drop=drop)
    else:
        submit_to_db(settings.papiex_output,settings.input_pattern,
                     dry_run=dry_run, drop=drop)

def compressed_tar(input):
    tar = None
    if (input.endswith("tar.gz") or input.endswith("tgz")):
        import tarfile
        tar = tarfile.open(input, "r:gz")
    elif (input.endswith("tar")):
        import tarfile
        tar = tarfile.open(input, "r:")
    return tar
    
def submit_to_db(input,pattern, dry_run=True, drop=False):
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
            info = tar.getmember("job_metadata")
        except KeyError:
            logger.error('ERROR: Did not find %s in tar archive' % "job_metadata")
            exit(1)
        else:
            logger.info('%s is %d bytes in archive' % (info.name, info.size))
            f = tar.extractfile(info)
            metadata = read_job_metadata_direct(f)
            filedict = get_filedict(None,pattern,tar)
    else:
        metadata = read_job_metadata(input+"job_metadata")
        filedict = get_filedict(input,pattern)

    logger.info("%d hosts found: %s",len(filedict.keys()),filedict.keys())
    for h in filedict.keys():
        logger.info("host %s: %d files to import",h,len(filedict[h]))

# Do as much as we can before bailing
    if dry_run:
        check_workflowdb_dict(metadata,pfx="exp_")
        logger.info("Dry run finished, skipping DB work")
        return

#    if tar:
#        tar.close()
#        logger.error('Unsupported at the moment.')
#        exit(1)

# Now we touch the Database
    from epmt_job import setup_orm_db
    setup_orm_db(drop)

    from epmt_job import ETL_job_dict, ETL_ppr
    j = ETL_job_dict(metadata,filedict,tarfile=tar)
    if not j:
        exit(1)
    logger.info("Committed job %s to database: %s",j.jobid,j)
# Check if we have anything related to an "experiment"

    if check_workflowdb_dict(metadata,pfx="exp_"):
        e = ETL_ppr(metadata,j.jobid)
        if not e:
            exit(1)
        logger.info("Committed post process run to database")    
#
# depends on args being global
#
def epmt_entrypoint(args, help):
    if not args.verbose:
        basicConfig(level=WARNING)
    elif args.verbose == 1:
        basicConfig(level=INFO)
    elif args.verbose >= 2:
        basicConfig(level=DEBUG)
    elif settings.debug:
        basicConfig(level=INFO)

    if args.help or args.epmt_cmd == 'help' or not args.epmt_cmd:
        help(stdout)
        dump_config(stdout)
        exit(0)

#        if args.auto or args.bash or args.csh:
#            if not args.epmt_cmd == "run":
#                logger.error("Arguments only valid with 'run' command")
#                exit(1)

    if args.epmt_cmd == 'dump':
        epmt_dump_metadata_file(args.epmt_cmd_args)
    elif args.epmt_cmd == 'start':
        set_job_globals(cmdline=args.epmt_cmd_args)
        epmt_start(from_batch=args.epmt_cmd_args)
    elif args.epmt_cmd == 'stop':
        set_job_globals(cmdline=args.epmt_cmd_args)
        epmt_stop(from_batch=args.epmt_cmd_args)
#	elif args.epmt_cmd == 'test':
#            set_job_globals(cmdline=args.epmt_cmd_args)
#            epmt_test_start_stop(from_batch=args.epmt_cmd_args)
    elif args.epmt_cmd == 'submit':
        # Not in job context
        if not args.epmt_cmd_args:
            a = [ get_job_dir() ]
        else:
            a = args.epmt_cmd_args
        epmt_submit_list(a,dry_run=args.dry_run,drop=args.drop)
    elif args.epmt_cmd == 'run':
        if args.epmt_cmd_args: 
            set_job_globals()
            exit(epmt_run(args.epmt_cmd_args,wrapit=args.auto,dry_run=args.dry_run,debug=(args.verbose > 2)))
        else:
            logger.error("No command given")
            exit(1)
    elif args.epmt_cmd == 'source':
        print epmt_source(False,settings.papiex_options,papiex_debug=(args.verbose > 2),monitor_debug=(args.verbose > 2))
    else:
        logger.error("Unknown command, %s. See -h for options.",args.epmt_cmd)
        exit(1)
    exit(0)

# Use of globals here is gross. FIX!
# 
# if (__name__ == "__main__"):

