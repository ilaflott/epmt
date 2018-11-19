#!/usr/bin/env python
from pony.orm import *
import settings
from models import db, Job, Host, Process, Thread, Metric
import os, sys, time, datetime
from pytz import UTC
from pytz import timezone
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

def sortKeyFunc(s):
    t = os.path.basename(s)
# skip papiex- and .csv
    t = t[7:-4]
# append instance number 
    t2 = t.split("-")
    return int(t2[0]+t2[1])

@db_session
def load_db_from_df(df, metricnames, jobid, hostname):
# Should look up first
	h = Host(name=hostname)
	print h
	j = Job(jobid=jobid)
	print j
	print "Adding process PID: "+str(df['pid'][0])
	p = Process(exename=df['exename'][0],args=df['args'][0],path=df['path'][0],pid=df['pid'][0],ppid=df['ppid'][0],pgid=df['pgid'][0],sid=df['sid'][0],gen=df['generation'][0],job=j,host=h)
	print p
	# Add threads
	for index, row in df.iterrows():
		print "Adding thread TID: "+str(row['tid']),row['start']
		start = pd.Timestamp(row['start'], unit='us')
		start = start.tz_localize(UTC)
		end = pd.Timestamp(row['end'], unit='us')
		end = end.tz_localize(UTC)
		t = Thread(tid=row['tid'],
			   time=start,
			   end=end,
			   duration=end-start,
			   process=p)
		print t
		p.threads.add(t)
		# Add metrics
		for metric in metricnames:
			print "Adding metric",metric,"value",df[metric][0]
			m = Metric(name=metric,value=df[metric][0],thread=t)
			print m
			t.metrics.add(m)

def load_jobcsv(jobid, hostname, pattern="papiex-[0-9]*-[0-9]*.csv", dirname="./sample-output/"):
# number of columns until caliper
	data_offset = 12
	print "Pattern:"+dirname+pattern
# Sort by PID
	files = glob.glob(dirname+pattern)
	for f in sorted(files,key=sortKeyFunc):
#		print "Processing:"+f
		dtype_dic = { 'exename':str, 'path':str, 'args':str} 
# columns here
#		dtype_dic2 = { 'start':datetime, 'end':datetime} 
# Damn NAN's for empty strings require converters
	        pf = pd.read_csv(f, converters=dtype_dic)
#		print pf.columns
# Force types (args may be empty which results in an float)		
#		pf['exename'] = pf['exename'].astype('object');
#		pf['args'] = pf['args'].astype('object');
#		pf['path'] = pf['path'].astype('object');
#		print pf.dtypes
#		print pf['args'].dtype
#		print pf['args'][0]
#		print "THERE"
		thread_cnt = len(pf.index)
		metric_cnt = len(pf.columns) - 12
		metric_names = pf.columns[12:].values.tolist()
		print thread_cnt, "threads with ", metric_cnt, "metrics", metric_names, "in", f 
#		print pf['tid']
		for index, row in pf.iterrows():
			print index,"TID: "+str(row['tid'])
		load_db_from_df(pf, metric_names, jobid, hostname)
		exit(0)
#		print "Made it"

try:
	# db.bind(provider='postgres', user='postgres', password='example', host='0.0.0.0', dbname='EPMT')
	db.bind(**settings.db_params)
	db.generate_mapping(create_tables=True)
except Exception as e:
    print("Database not found",e)
    exit(1)

#try:
#	test_insert(1)
#	test_query(1)
load_jobcsv(4,"hostname.foo.com")
#except Exception as exception:
#	print type(exception).__name__,exception.args#
#	exit(1)

#with db_session:
#	h = Host(dbname="one",jobid=234)



#if __name__ == '__name__':
#	app = App()
#	app.run()
