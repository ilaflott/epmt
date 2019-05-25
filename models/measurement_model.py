#
# Physical/measurement model 
#

from pony.orm import *
from .general import db
import datetime

class Tag(db.Entity):
#	time = Required(datetime.datetime, default=datetime.datetime.utcnow)
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow)
	info_dict = Optional(Json)
	# end template
	name = PrimaryKey(str)
	processes = Set('Process')
	jobs = Set('Job')
#
# Removing/changing hosts needs to be addressed
#
class Host(db.Entity):
#	time = Required(datetime.datetime, default=datetime.datetime.utcnow)
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
# End rollups
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
	tags = Set('Tag')
	account = Optional('Account')
	queue = Optional('Queue')
	ppr = Optional('PostProcessRun')

class Process(db.Entity):
# Rollup entries, computed at insert time
	start = Required(datetime.datetime, default=datetime.datetime.utcnow)
	end = Required(datetime.datetime, default=datetime.datetime.utcnow)
	duration = Required(float, default=0)
# End rollup
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow)
#	info_dict = Optional(Json)
# End generic template
	tags = Set('Tag')
	job = Required('Job')
	host = Required('Host')
	user = Required('User')
	group = Optional('Group')
	threads = Set('Thread')
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

class Thread(db.Entity):
# These are measured
	start = Required(datetime.datetime)
	end = Required(datetime.datetime)
# This is computed at insert time
	duration = Required(float)
#	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow)
#	info_dict = Optional(Json)
# End generic template
	tid = Required(int)
	metrics = Set('Metric')
	process = Required(Process)
#	calipers = Set('Calipers')

#class Caliper(db.Entity):
#	name = Required(str)
#	metrics = Set('Metric')
#   duration = Required(datetime.timedelta)
#	parent = Required(Thread) # Fix: Could be process or host

class MetricName(db.Entity):
	name = PrimaryKey(str)
	metrics = Set('Metric')

class Metric(db.Entity):
	metricname = Required('MetricName')
	value = Required(float)
	thread = Required(Thread)

class User(db.Entity):
	time = Required(datetime.datetime, default=datetime.datetime.utcnow)
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow)
	info_dict = Optional(Json)
	# end template
	name = PrimaryKey(str)
	id = Optional(int,unique=True)
	groups = Set('Group')
#	exps = Set('Experiment')
	pprs = Set('PostProcessRun')
	jobs = Set('Job')
	processes = Set('Process')

class Group(db.Entity):
	time = Required(datetime.datetime, default=datetime.datetime.utcnow)
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow)
	info_dict = Optional(Json)
	# end template
	name = PrimaryKey(str)
	id = Required(int,unique=True)
	jobs = Set('Job')
	processes = Set('Process')
	users = Set('User')

class Queue(db.Entity):
	time = Required(datetime.datetime, default=datetime.datetime.utcnow)
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow)
	info_dict = Optional(Json)
	# end template
	name = PrimaryKey(str)
	id = Optional(int,unique=True)
	jobs = Set('Job')	

class Account(db.Entity):
	time = Required(datetime.datetime, default=datetime.datetime.utcnow)
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow)
	info_dict = Optional(Json)
	# end template
	name = PrimaryKey(str)
	id = Optional(int,unique=True)
	jobs = Set('Job')	
