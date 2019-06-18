#
# Physical/measurement model 
#

from pony.orm import *
from .general import db
import datetime

# Removing/changing hosts needs to be addressed
#
class Host(db.Entity):
	created_at = Required(datetime.datetime, default=datetime.datetime.utcnow)
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow)
	info_dict = Optional(Json)
	# end template
	name = PrimaryKey(str)
	processes = Set('Process')
	jobs = Set('Job')
#
# A job is a separate but possibly connected entity to an experiment/postprocess run
#
class Job(db.Entity):
# Rollup entries, computed at insert time
	start = Required(datetime.datetime, default=datetime.datetime.utcnow)
	end = Required(datetime.datetime, default=datetime.datetime.utcnow)
	duration = Required(float, default=0)
	proc_sums = Optional(Json) # proc_sums contains aggregates across processes
# End rollups
	created_at = Required(datetime.datetime, default=datetime.datetime.utcnow)
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow)
	info_dict = Optional(Json)
# End generic template
	env_dict = Optional(Json)
	env_changes_dict = Optional(Json)
	submit = Optional(datetime.datetime)
	jobid = PrimaryKey(str)
	jobname = Optional(str)
	jobscriptname = Optional(str)
	sessionid = Optional(int)
	exitcode = Optional(int)
	user = Required('User')
	groups = Set('Group')
	hosts = Set('Host')
	processes = Set('Process')
	tags = Optional(Json)
	account = Optional('Account')
	queue = Optional('Queue')
#	ppr = Optional('PostProcessRun')
	cpu_time = Optional(float)
	ref_models = Set('ReferenceModel')

class Process(db.Entity):
# Rollup entries, computed at insert time
	start = Required(datetime.datetime, default=datetime.datetime.utcnow)
	end = Required(datetime.datetime, default=datetime.datetime.utcnow)
	duration = Required(float, default=0)
# End rollup
	created_at = Required(datetime.datetime, default=datetime.datetime.utcnow)
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow)
#	info_dict = Optional(Json)
# End generic template
	tags = Optional(Json)
	job = Required('Job')
	host = Required('Host')
	user = Required('User')
	group = Optional('Group')
	threads_df = Optional(Json)
	threads_sums = Optional(Json)
	numtids = Required(int, default=1)
# save some useful timing information for threads
	exclusive_cpu_time = Optional(float)
# sum of cpu times of all descendants + process_cpu_time
	inclusive_cpu_time = Optional(float)
# These should probably be abstracted/reduced
	exename = Required(str)
	path = Required(str)
	args = Optional(str)
#	env_dict = Optional(Json)
# End above
	pid = Required(int)
	ppid = Required(int)
	pgid = Required(int)
	sid = Required(int)
	gen = Required(int)
	exitcode = Optional(int)
# for creating a process graph
# a child process is also included in the list of descendants
# while parent is included in the ancestors
	parent = Optional('Process', reverse="children")
	children = Set('Process', reverse="parent")
	ancestors = Set('Process', reverse="descendants")
	descendants = Set('Process', reverse="ancestors")

	ref_models = Set('ReferenceModel')

# class Thread(db.Entity):
# # These are measured
# 	start = Required(datetime.datetime)
# 	end = Required(datetime.datetime)
# # This is computed at insert time
# 	duration = Required(float)
# #	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow)
# #	info_dict = Optional(Json)
# # End generic template
# 	tid = Required(int)
# 	metrics = Optional(Json)
# 	process = Required(Process)
# #	calipers = Set('Calipers')

#class Caliper(db.Entity):
#	name = Required(str)
#	metrics = Set('Metric')
#   duration = Required(datetime.timedelta)
#	parent = Required(Thread) # Fix: Could be process or host

# class MetricName(db.Entity):
# 	name = PrimaryKey(str)
# 	metrics = Set('Metric')

# class Metric(db.Entity):
# 	metricname = Required('MetricName')
# 	value = Required(float)
# 	thread = Required(Thread)

class User(db.Entity):
	created_at = Required(datetime.datetime, default=datetime.datetime.utcnow)
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow)
	info_dict = Optional(Json)
	# end template
	name = PrimaryKey(str)
	id = Optional(int,unique=True)
	groups = Set('Group')
#	exps = Set('Experiment')
#	pprs = Set('PostProcessRun')
	jobs = Set('Job')
	processes = Set('Process')

class Group(db.Entity):
	created_at = Required(datetime.datetime, default=datetime.datetime.utcnow)
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow)
	info_dict = Optional(Json)
	# end template
	name = PrimaryKey(str)
	id = Required(int,unique=True)
	jobs = Set('Job')
	processes = Set('Process')
	users = Set('User')

class Queue(db.Entity):
	created_at = Required(datetime.datetime, default=datetime.datetime.utcnow)
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow)
	info_dict = Optional(Json)
	# end template
	name = PrimaryKey(str)
	id = Optional(int,unique=True)
	jobs = Set('Job')	

class Account(db.Entity):
	created_at = Required(datetime.datetime, default=datetime.datetime.utcnow)
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow)
	info_dict = Optional(Json)
	# end template
	name = PrimaryKey(str)
	id = Optional(int,unique=True)
	jobs = Set('Job')	
