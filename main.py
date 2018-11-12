#!/usr/bin/env python
from pony.orm import *
import settings
from models import db, Job, Host, Process, Thread, Metric
import sys, time, datetime

# 
# Logical Model
#
@db_session
def test_insert(jobid):
		j = Job(jobid=jobid)
		h = Host(name = "foo.bar.com")
		p = Process(exename='a.out', path='/home/phil', host=h, pid=1011, ppid=1, sid=1, job=j)
		t = Thread(tid=1011, duration=datetime.timedelta(minutes=1),process=p)
		m1 = Metric(name='cycles', value=1001, threads=[t])
		m2 = Metric(name='bytes', value=2002, threads=[t])
		t.metrics = [ m1, m2 ]
		p.threads = [ t ]
		j.processes = [ p ]

@db_session
def test_query(jobid):
	t = Job[jobid]
	print t.jobid
	for p in t.processes:
		print p.exename
		for t in p.threads:
			for m in t.metrics:
				print m.name, m.value
		


try:
	# db.bind(provider='postgres', user='postgres', password='example', host='0.0.0.0', dbname='EPMT')
	db.bind(**settings.db_params)
	db.generate_mapping(create_tables=True)
except Exception as e:
    print("Database not found",e)
    exit(1)

try:
	test_insert(1)
except Exception as exception:
	print type(exception).__name__,exception.args
	exit(1)

test_query(1)

#if __name__ == '__name__':
#	app = App()
#	app.run()
