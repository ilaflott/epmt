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
	jobid = Required(int, unique=True)
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
	sid = Required(int)

class Thread(db.Entity):
	time = Required(datetime.datetime, default=datetime.datetime.utcnow())
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
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

class Metric(db.Entity):
	name = Required(str)
	value = Required(float)
	threads = Set(Thread)

# Removing/changing hosts needs to be addressed
class Host(db.Entity):
	time = Required(datetime.datetime, default=datetime.datetime.utcnow())
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
	info_dict = Optional(Json)
	# end template
	name = Required(str,unique=True)
	ipaddr = Optional(str)
	processes = Set(Process)
	

