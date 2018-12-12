#!/usr/bin/env python
#import settings
#from models import db, db_session, User, Platform, Experiment, PostProcessRun
from logging import getLogger, basicConfig, DEBUG, INFO, WARNING, ERROR
from datetime import datetime
from os import environ, makedirs, errno
from socket import gethostname
from json import dumps as dict_to_json
from subprocess import call as forkexec
from random import randint
import pickle
import argparse
from dictdiffer import diff

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

def create_job_prolog(jobid, from_batch=[]):
	retval = {}
	ts=datetime.now()
	env=blacklist_filter(filter,**environ)
#	print env
	retval['job_pl_id'] = jobid
	retval['job_pl_scriptname'] = "job_scriptname"
	retval['job_pl_hostname'] = gethostname()
	retval['job_pl_env_len'] = len(env)
	retval['job_pl_env'] = env
	retval['job_pl_start'] = ts
	retval['job_pl_from_batch'] = from_batch

	return retval

def create_job_epilog(prolog, from_batch=[], status="0"):
	retval = {}
	ts=datetime.now()
	env=blacklist_filter(filter,**environ)
	env = list(diff(prolog['job_pl_env'],env))
	retval['job_el_env_changes_len'] = len(env)
	retval['job_el_env_changes'] = env
	retval['job_el_stop'] = ts
	retval['job_el_from_batch'] = from_batch
	retval['job_el_status'] = status

	return retval

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
	if environ.get('PBS_JOBID'):
		return environ['PBS_JOBID']
	elif environ.get('SLURM_JOBID'):
		return environ['SLURM_JOBID']
	else:
#		r=randint(0,1000000000)
#		logger.warn("Using random number %d for JobID",r)
		return str(1) #r

def get_job_dir(jobid=get_job_id(), hostname="", prefix="/tmp/epmt/"):
	return prefix+jobid
def get_job_file(jobid=get_job_id(), hostname="", prefix="/tmp/epmt/"):
	s = get_job_dir(jobid,hostname,prefix)
	return s+"/job_metadata"

def create_job_dir(dir=get_job_dir()):
	try:
		makedirs(dir, 0700) 
	except OSError, e:
		if e.errno != errno.EEXIST:
			logger.debug("dir %s: %s",dir,e)
			return s
	logger.debug("created dir (or it existed) %s",dir)
	return dir

#
#
#
#db.bind(**settings.db_params)
def epmt_start(from_batch=[]):
	jobid = get_job_id()
	dir = create_job_dir()
	if dir is False:
		exit(1)
	file = get_job_file()
	d = create_job_prolog(jobid,from_batch)
	write_job_prolog(file,d)
	logger.info("wrote prolog %s",file);
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
	logger.info("wrote prolog %s",file);
	logger.info("job start: %s",metadata['job_pl_start'])
	logger.info("job stop: %s",metadata['job_el_stop'])
	logger.info("job duration:  %s",metadata['job_el_stop'] - metadata['job_pl_start'])
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
	

if (__name__ == "__main__"):
	parser=argparse.ArgumentParser(description="...")
	parser.add_argument('pos_arg',type=str,help="A command: start, stop, test");
	parser.add_argument('other_args',nargs='*',help="Additional arguments from calling scripts");
	parser.add_argument('--debug',action='store_true',help="Debug mode, verbose")
	args = parser.parse_args()
	if args.debug:
		basicConfig(level=DEBUG)
	else:
		basicConfig(level=INFO)
		
	if args.pos_arg == 'start':
		epmt_start(from_batch=args.other_args)
	elif args.pos_arg == 'stop':
		epmt_stop(from_batch=args.other_args)
	elif args.pos_arg == 'test':
		epmt_test_start_stop(from_batch=args.other_args)
	

	
# 	print (d == d2)
# 	print d
# 	print
# 	print
# 	d3 = create_job_epilog(jobid)
# 	write_job_epilog(dir+"/job_metadata",d3)
# 	print d4

# #	exitcode, stdout, stderr = job_run(["echo","message from echo"])
# #	job_epilog()
