#!/usr/bin/env python
from pony.orm import *
import settings
from models import db, Job, Host, Process, Thread, Metric
import sys, time, datetime
import pandas as pd
import glob
# 
# Logical Model
#
@db_session
def test_insert(jobid):
		h = Host(name="foo.bar.com")
		j = Job(jobid=jobid)
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

def load_jobcsv(jobid, hostname, pattern="job-[0-9]*.csv", dirname="./"):
	print dirname+pattern
	print glob.glob(dirname+pattern)
	for f in glob.glob(dirname+pattern):
		print f
		pf = pd.read_csv(f)
		print pf
		thread_cnt = len(pf.index)
		metric_cnt = len(pf.columns) - 8
		metric_names = pf.columns[8:].values.tolist()
		print thread_cnt, "threads with ", metric_cnt, "metrics", metric_names 
#		print pf['tid']
		for index, row in pf.iterrows():
			print row['tid']

try:
	# db.bind(provider='postgres', user='postgres', password='example', host='0.0.0.0', dbname='EPMT')
	db.bind(**settings.db_params)
	db.generate_mapping(create_tables=True)
except Exception as e:
    print("Database not found",e)
    exit(1)

try:
	test_insert(1)
	test_query(1)
	load_jobcsv(hostname="foo.bar.com", jobid=2)
except Exception as exception:
	print type(exception).__name__,exception.args
	exit(1)



#if __name__ == '__name__':
#	app = App()
#	app.run()
