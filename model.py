#!/usr/bin/env python
import sys
from pony.orm import *
db = Database()

class Job(db.Entity):
	jobid = Required(int, unique=True)
	processes = Set('Process')
class Process(db.Entity):
	name = Required(str)
	threads = Set('Thread')
	parent = Required(Job)
class Thread(db.Entity):
	metrics = Set('Metrics')
	parent = Required(Process)
class Metrics(db.Entity):
	name = Required(str)
	value = Required(int)
	parent = Required(Thread)

@db_session
def test_insert(jobid):
		j = Job(jobid=jobid)
		p = Process(name='a.out', parent=j)
		t = Thread(parent = p)
		Metrics(name='cycles', value=1001, parent=t)
		Metrics(name='bytes', value=2002, parent=t)

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
	db.bind(provider='postgres', user='postgres', password='example', host='0.0.0.0', dbname='EPMT')
	db.generate_mapping(create_tables=True)
except:
        print("Database not found") 
	exit(1)
#db.bind(provider='sqlite', filename=":memory:")
# db.bind(provider='postgres', user='', password='', host='', database='')
#db.generate_mapping(create_tables=True)
#set_sql_debug(True)

try:
	test_insert(1)
except Exception as exception:
	print type(exception).__name__,exception.args

test_query(1)
