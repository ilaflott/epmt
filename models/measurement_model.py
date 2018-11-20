#
# Physical/measurement model 
#

from pony.orm import *
import time, datetime
from .general import db

# A job doesn't have to be part of an experiment or postprocess run
class Job(db.Entity):
	time = Required(datetime.datetime, default=datetime.datetime.utcnow())
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
	duration = Optional(datetime.timedelta)
	info_dict = Optional(Json)
	# end template
	jobid = PrimaryKey(int)
	processes = Set('Process')
	ppr = Optional('PostProcessRun')

class Process(db.Entity):
	time = Required(datetime.datetime, default=datetime.datetime.utcnow())
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
	duration = Optional(datetime.timedelta)
	info_dict = Optional(Json)
	# end template
	job = Required('Job')
	host = Required('Host')
	threads = Set('Thread')
	exename = Required(str)
	path = Required(str)
	args = Optional(str)
	pid = Required(int)
	ppid = Required(int)
	pgid = Required(int)
	sid = Required(int)
	gen = Required(int)

class Thread(db.Entity):
	time = Required(datetime.datetime)
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
	end = Required(datetime.datetime)
	duration = Required(datetime.timedelta)
	info_dict = Optional(Json)
	# end template
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

# Removing/changing hosts needs to be addressed
class Host(db.Entity):
	# time = Required(datetime.datetime, default=datetime.datetime.utcnow())
	# updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
	#info_dict = Optional(Json)
	# end template
	name = PrimaryKey(str)
	#ipaddr = Optional(str)
	processes = Set(Process)
