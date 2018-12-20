#!/usr/bin/env python
import settings
#from models import db, db_session, User, Platform, Experiment, PostProcessRun
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
import pickle
import argparse

def getgroups(user):
    gids = [g.gr_gid for g in getgrall() if user in g.gr_mem]
    gid = getpwnam(user).pw_gid
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
		logger.warn("Using session id %s as JOB_ID",global_job_id)

	global_job_name = get_job_var("JOB_NAME")
	if not global_job_name:
		if cmdline:
			global_job_name=' '.join(cmdline)
			logger.warn("Using command line %s as JOB_NAME",global_job_name)
		else:
			global_job_name=str(getpid())
			logger.warn("Using process id %s as JOB_NAME",global_job_name)

	global_job_scriptname = get_job_var("JOB_SCRIPTNAME")
	if not global_job_scriptname:
		global_job_scriptname=global_job_name
		logger.warn("Using process name %s as JOB_SCRIPTNAME",global_job_name)

	global_job_username = get_job_var("JOB_USER")
	if not global_job_username:
		global_job_username = getpwuid(getuid()).pw_name
		logger.warn("Using username %s as JOB_USER",global_job_username)

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

def job_epilog(jobdatafile="unknown_job.jobid", exitcode=0, stdout=None, stderr=None):
	# timestamp
	ts=datetime.now()
	with open(jobdatafile,'a') as file:
		logger.debug("Exitcode: %s",str(exitcode))
		file.write(str(exitcode))
		logger.debug("Time finish: %s",str(ts))
		file.write(str(ts))
	logger.debug("Appended to "+jobdatafile)
	# collect env

def job_run(argvlist):
	stdout = None
	stderr = None
# Ideally we could capture job output here too
	if argvlist:
		return forkexec(argvlist),stdout,stderr
	else:
		return 256,stdout,stderr

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

def create_job_epilog(prolog, from_batch=[], status="0"):
	metadata = {}
	ts=datetime.now()
	env=blacklist_filter(filter,**environ)
        try:
            find_module('dictdiffer')
            import dictdiffer
            env = list(dictdiffer.diff(prolog['job_pl_env'],env))
        except ImportError:
            logger.warn("dictdiffer module not found");
            env = env
	metadata['job_el_env_changes_len'] = len(env)
	metadata['job_el_env_changes'] = env
	metadata['job_el_stop'] = ts
	metadata['job_el_from_batch'] = from_batch
	metadata['job_el_status'] = status

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

def read_job_metadata(jobdatafile):
	data = False
	logger.debug("Unpickling from "+jobdatafile)
	with open(jobdatafile,'rb') as file:
		data = pickle.load(file)
		logger.debug("Unpickled from "+jobdatafile)
	return data
	# collect env

def write_job_epilog(jobdatafile,metadata):
	with open(jobdatafile,'w+b') as file:
		pickle.dump(metadata,file)
		logger.debug("Pickled to "+jobdatafile)
		return True
	return False
	# collect env

# Clean files from tmp storage
def job_clean():
	return True

# Gather files from tmp storage to persistant storage
def job_gather():
	return True

def get_job_id():
	global global_job_id
	return(global_job_id)

def get_job_dir(hostname="", prefix="/tmp/epmt/"):
	global global_job_id
	return prefix+global_job_id

def get_job_file(hostname="", prefix="/tmp/epmt/"):
	s = get_job_dir(hostname,prefix)
	return s+"/job_metadata"

def create_job_dir(dir):
	try:
		makedirs(dir, 0700) 
		logger.debug("created dir %s",dir)
	except OSError, e:
		if e.errno != errno.EEXIST:
			logger.error("dir %s: %s",dir,e)
			return s
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
	file = get_job_file()
	d = create_job_prolog(jobid,from_batch)
	write_job_prolog(file,d)
	logger.info("wrote prolog %s",file);
	logger.debug("%s",metadata)
	return d

def epmt_stop(from_batch=[]):
	jobid = get_job_id()
	file = get_job_file()
	if file is False:
		exit(1)
	prolog = read_job_metadata(file)
	if not prolog:
		return False
	logger.info("read prolog %s",file);
	epilog = create_job_epilog(prolog,from_batch)
	metadata = merge_two_dicts(prolog,epilog)
	write_job_epilog(file,metadata)
	logger.info("wrote epilog %s",file);
	logger.debug("%s",metadata)
	return metadata


def epmt_test_start_stop(from_batch=[]):
	d1 = epmt_start(from_batch)
	environ['INSERTED_ENV'] = "Yessir!"
	d2 = epmt_stop(from_batch)
 	d3 = merge_two_dicts(d1,d2)
 	d4 = read_job_metadata(jobdatafile=get_job_file())
 	print "Test is",(d3 == d4)
	if (d3 != d4):
		exit(1)
	print d4
	
def epmt_run(cmdline, wrapit=True):
	logger.debug(cmdline)
	started = False
	file = get_job_file()
	if wrapit and not path.exists(file):
		epmt_start()
		started = True
	t = environ.get("PAPIEX_OSS_PATH")
	if t and path.exists(t):
		logger.info("Overriding settings.install_prefix with PAPIEX_OSS_PATH=",t)
		settings.install_prefix = t
	cmd =  "PAPIEX_OPTIONS=PERF_COUNT_SW_CPU_CLOCK "
	cmd += "PAPIEX_OUTPUT="+get_job_dir()+" "
	cmd += settings.install_prefix+"/bin/monitor-run -i "+settings.install_prefix+"/lib/libpapiex.so "+" ".join(cmdline)
	print cmd
	return_code = forkexecwait(cmd, shell=True)
	if started:
		epmt_stop()
		started = False
	return return_code

def db_submit_job(metadata, filedict):
    import epmt_job
#    logger.info("%s",metadata)
#    logger.info("%s",filedict)
    return True

def epmt_submit(directory="/tmp/epmt/",pattern=settings.input_pattern):
#    if not jobid:
#        logger.error("Job ID is empty!");
#        exit(1);
    from epmt_job import get_filedict, ETL_job_dict
    t = environ.get("PAPIEX_OUTPUT")
    if t and path.exists(t):
        dirname = t
    else:
        dirname = directory
    if not dirname.endswith("/"):
        logger.error("Warning missing trailing / on %s",dirname);
        dirname += "/"
    metafile = dirname+"job_metadata"
    metadata = read_job_metadata(metafile)
    filedict = get_filedict(dirname,pattern)
    logger.info("%d hosts found: %s",len(filedict.keys()),filedict.keys())
    for h in filedict.keys():
        logger.info("host %s: %d files",h,len(filedict[h]))
    exit(ETL_job_dict(metadata,filedict))

# Use of globals here is gross. FIX!

if (__name__ == "__main__"):
	parser=argparse.ArgumentParser(description="...")
	parser.add_argument('epmt_cmd',type=str,help="start, run, stop, test");
	parser.add_argument('other_args',nargs='*',help="Additional arguments from calling scripts");
	parser.add_argument('--debug',action='store_true',help="Debug mode, verbose")
	args = parser.parse_args()
	if args.debug:
		basicConfig(level=DEBUG)
	else:
		basicConfig(level=INFO)

	if args.epmt_cmd == 'start':
            set_job_globals(cmdline=args.other_args)
            epmt_start(from_batch=args.other_args)
	elif args.epmt_cmd == 'stop':
            set_job_globals(cmdline=args.other_args)
            epmt_stop(from_batch=args.other_args)
	elif args.epmt_cmd == 'test':
            set_job_globals(cmdline=args.other_args)
            epmt_test_start_stop(from_batch=args.other_args)
	elif args.epmt_cmd == 'submit':
            if len(args.other_args) == 1: 
                epmt_submit(args.other_args[0],pattern="papiex*.csv")
            else:
                logger.error("<directory> required as argument")
                exit(1)
#                set_job_globals(cmdline=args.other_args)
#                epmt_submit(global_job_id)
	elif args.epmt_cmd == 'run':
            set_job_globals(cmdline=args.other_args)
            if args.other_args: 
                epmt_run(args.other_args)
            else:
                logger.warning("no run command given")
                exit(1)
