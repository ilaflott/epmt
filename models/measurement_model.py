#
# Physical/measurement model 
#

from pony.orm import *
from .general import db
import datetime
#
# A job is a separate but possibly connected entity to an experiment/postprocess run
#
class Job(db.Entity):
# Rollup entries, computed at insert time
	start = Required(datetime.datetime, default=datetime.datetime.utcnow())
	end = Required(datetime.datetime, default=datetime.datetime.fromtimestamp(0))
	duration = Required(int, default=0)
# End rollups
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
	info_dict = Optional(Json)
# End generic template
	submit = Optional(datetime.datetime)
	jobid = PrimaryKey(int)
	processes = Set('Process')
	ppr = Optional('PostProcessRun')

class Process(db.Entity):
# Rollup entries, computed at insert time
	start = Required(datetime.datetime, default=datetime.datetime.utcnow())
	end = Required(datetime.datetime, default=datetime.datetime.fromtimestamp(0))
	duration = Required(int, default=0)
# End rollup
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
	info_dict = Optional(Json)
# End generic template
	job = Required('Job')
	host = Required('Host')
	threads = Set('Thread')
# These should probably be abstracted/reduced
	exename = Required(str)
	path = Required(str)
	args = Optional(str)
# End above
	pid = Required(int)
	ppid = Required(int)
	pgid = Required(int)
	sid = Required(int)
	gen = Required(int)

class Thread(db.Entity):
# These are measured
	start = Required(datetime.datetime)
	end = Required(datetime.datetime)
# This is computed at insert time
	duration = Required(int)
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
	info_dict = Optional(Json)
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

# Removing/changing hosts needs to be addressed
class Host(db.Entity):
	# time = Required(datetime.datetime, default=datetime.datetime.utcnow())
	# updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
	#info_dict = Optional(Json)
	# end template
	name = PrimaryKey(str)
	#ipaddr = Optional(str)
	processes = Set(Process)
