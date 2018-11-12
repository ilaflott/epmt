#!/usr/bin/env python
import sys
from pony.orm import *
import time, datetime

db = Database()
# 
# Logical Model
#

# User running experiment or frepp
class User(db.Entity):
	time = Required(datetime.datetime, default=datetime.datetime.utcnow())
	username = Required(str)
	contact_dict = Optional(Json)
	experiments = Set('ModelRun')
#	frepps = Set('PostProcessRun')
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
# Build/version/etc
class Platform(db.Entity):
	time = Required(datetime.datetime, default=datetime.datetime.utcnow())
	name = Required(str)
	platform_dict = Optional(Json)
	experiments = Set('Experiment')
#	frepps = Set('PostProcessRun')
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
# Frerun
class Experiment(db.Entity):
	time = Required(datetime.datetime, default=datetime.datetime.utcnow())
	frepps = Set('PostProcessRun')
	metadata_dict = Optional(Json)
	user = Required(User)
	platform = Required(Platform)
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
# Frepp
class PostProcessRun(db.Entity):
	time = Required(datetime.datetime, default=datetime.datetime.utcnow())
	fullcommand = Required(str)
	xmlfile = Required(str)
	indir = Required(str)
	outdir = Required(str)
	metadata_dict = Optional(Json)
	jobs = Set('Job')
	experiment = Required(Experiment)
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
#
# Physical model 
#

# Base class
class MyEntity(db.Entity):
	tag_dict = Optional(Json)
	time = Required(datetime.time)
	duration = Required(datetime.time)
	updated_at = Required(datetime.datetime, default=datetime.datetime.utcnow())
	metrics = Set('Metric')
	parent = Required('Thread', 'Process', 'Job', 'Host')

# A job doesn't have to be part of an experiment or postprocess run
class Job(MyEntity):
	jobid = Required(int, unique=True)
	processes = Set('Process')
	hosts = Set('Host')
	ppr = Optional('PostProcessRun')

class Process(MyEntity):
	exename = Required(str)
	path = Required(str)
	args = Optional(str)
	host = Required('Host')
	pid = Required(int)
	ppid = Required(int)
	sid = Required(int)
	threads = Set('Thread')

class Thread(MyEntity):
	tid = Required(int)
#	calipers = Set('Calipers')
#class Caliper(MyEntity):
#	name = Required(str)
#	metrics = Set('Metric')
#	parent = Required(Thread) # Fix: Could be process or host

# Support classes
class Metric(db.Entity):
	name = Required(str)
	value = Required(float)
# Removing/changing hosts needs to be addressed
class Host(db.Entity):
	name = Required(str,unique=True)
	ipaddr = Optional(str)
	metadata_dict = Optional(Json)
	
@db_session
def test_insert(jobid):
		j = Job(jobid=jobid,time=1)
		h = Host(name = "foo.bar.com")
		p = Process(exename='a.out', path='/home/phil', host=h, pid=1011, ppid=1, sid=1, parent=j, time=2)
		t = Thread(tid=1011, parent=p, time=3)
		m1 = Metric(name='cycles', value=1001, parent=t, time=4.1)
		m2 = Metric(name='bytes', value=2002, parent=t, time=4.2)
		t.metrics = [ m1, m2 ]
		p.threads = [ t ]
		j.processes = [ p ]

@db_session
def test_query(jobid):
	t = Job[jobid]
	print t.jobid
	for p in t.processes:
		print p.name
		for t in p.threads:
			for m in t.metrics:
				print m.name, m.value
		


try:
	# db.bind(provider='postgres', user='postgres', password='example', host='0.0.0.0', dbname='EPMT')
	db.bind(provider='sqlite', filename=":memory:")
	db.generate_mapping(create_tables=True)
except Exception as e:
        print("Database not found",e) 
	exit(1)
#
# db.bind(provider='postgres', user='', password='', host='', database='')
#db.generate_mapping(create_tables=True)
#set_sql_debug(True)

try:
	test_insert(1)
except Exception as exception:
	print type(exception).__name__,exception.args

test_query(1)
