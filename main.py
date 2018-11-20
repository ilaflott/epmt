#!/usr/bin/env python
import settings
from pony.orm import *
from models import *
import os, sys, time, datetime
from pytz import UTC
from pytz import timezone
import pandas as pd
import glob
import itertools
spinner = itertools.cycle(['-', '/', '|', '\\'])

def dprint(*args):
	if (settings.debug): print args
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
def lookup_or_create_metricname(metricname):
	mn = MetricName.get(name=metricname)
	if mn is None:
		dprint("Creating metric",metricname)
		mn = MetricName(name=metricname)
#	print mn
	return mn

@db_session
def lookup_or_create_job(jobid):
	job = Job.get(jobid=jobid)
	if job is None:
		dprint("Creating job",jobid)
		job = Job(jobid=jobid)
#	print job
	return job

@db_session
def lookup_or_create_host(hostname):
	host = Host.get(name=hostname)
	if host is None:
		dprint("Creating host",hostname)
		host = Host(name=hostname)
#	print host
	return host

@db_session
def load_process_from_pandas(df, h, j, mns):
# Assumes all processes are from same host
#	dprint("Creating process",str(df['pid'][0]),"gen",str(df['generation'][0]),"exename",df['exename'][0])
	p = Process(exename=df['exename'][0],
		    args=df['args'][0],
		    path=df['path'][0],
		    pid=int(df['pid'][0]),
		    ppid=int(df['ppid'][0]),
		    pgid=int(df['pgid'][0]),
		    sid=int(df['sid'][0]),
		    gen=int(df['generation'][0]),
		    job=j,
		    host=h)
#	print p
	# Add all threads
	for index, row in df.iterrows():
#		print "Adding thread TID: "+str(row['tid']),row['start']
		start = pd.Timestamp(row['start'], unit='us')
#		start = start.tz_localize(UTC)
		end = pd.Timestamp(row['end'], unit='us')
#		end = end.tz_localize(UTC)
		duration = end-start
#		dprint("Creating thread",str(row['tid']),"start",start,"end",end,"duration",duration)
		t = Thread(tid=row['tid'],
			   time=start,
			   end=end,
			   duration=duration,
			   process=p)
#		print t
#		p.threads.add(t)
		# Add metrics
		for metric,obj in mns.iteritems():
#			dprint("Creating metric",metric,"value",df[metric][0])
			m = Metric(metricname=obj,value=df[metric][0],thread=t)
#			print m
#			t.metrics.add(m)a

@db_session
def load_job_from_dirofcsvs(jobid, hostname, pattern="papiex-[0-9]*-[0-9]*.csv", dirname="./sample-output/"):
# Damn NAN's for empty strings require converters, and empty integers need floats
	conv_dic = { 'exename':str, 
		     'path':str, 
		     'args':str } 
	dtype_dic = { 
		'pid':                        float,
		'generation':                 float,
		'ppid':                       float,
		'pgid':                       float,
		'sid':                        float,
		'numtids':                    float }
#	data_offset = settings.metrics_offset
#	print "Pattern:"+dirname+pattern
	files = sorted(glob.glob(dirname+pattern),key=sortKeyFunc)
# Sort by PID
	then = datetime.datetime.now()
	csvt = datetime.timedelta()
	ponyt = datetime.timedelta()
	sys.stdout.write('-')
# Hostname, job, metricname objects
	h = None
	m = None
	mns = {}
# Iterate over files 
	for f in files:
		sys.stdout.write('\b')            # erase the last written char
		sys.stdout.write(spinner.next())  # write the next character
		sys.stdout.flush()                # flush stdout buffer (actual character display)
#		print f
		csv = datetime.datetime.now()
	        pf = pd.read_csv(f,
				 dtype=dtype_dic, 
				 converters=conv_dic)
		csvt += datetime.datetime.now() - csv
# Lookup or create the necessary objects, only happens once!
		if h is None:
			for metric in pf.columns[settings.metrics_offset:].values.tolist():
				mns[metric] = lookup_or_create_metricname(metric)
			j = lookup_or_create_job(jobid)
			h = lookup_or_create_host(hostname)

#		print pf.columns
# Force types (args may be empty which results in an float)		
#		pf['exename'] = pf['exename'].astype('object');
#		pf['args'] = pf['args'].astype('object');
#		pf['path'] = pf['path'].astype('object');
#		print pf.dtypes
#		print pf['args'].dtype
#		print pf['args'][0]
#		print "THERE"
#		thread_cnt = len(pf.index)
#		metric_cnt = len(pf.columns) - settings.metrics_offset
#		metric_names = pf.columns[settings.metrics_offset:].values.tolist()
#		dprint (f,": Read",thread_cnt,"threads with ",metric_cnt,"metrics",metric_names)
#		print pf['tid']
#		for index, row in pf.iterrows():
#			print index,"TID: "+str(row['tid'])
		pony = datetime.datetime.now()
		load_process_from_pandas(pf, h, j, mns)
		ponyt += datetime.datetime.now() - pony
	sys.stdout.write('\b')            # erase the last written char
	print len(files),"files imported,", datetime.datetime.now() - then,"seconds,",len(files)/float((datetime.datetime.now() - then).seconds),"per second."
	print "load_process_from_pandas()", ponyt, "\nread_csv()", csvt
#		exit(0)
#		print "Made it"

db.bind(**settings.db_params)
db.generate_mapping(create_tables=True)
load_job_from_dirofcsvs(4,"hostname.foo.com")
	#       db.bind(provider='postgres', user='postgres', password='example', host='0.0.0.0', dbname='EPMT')
	# 	db.drop_all_tables(with_all_data=True)
	#	db.create_tables()
#try:
#	test_insert(1)
#	test_query(1)
#except Exception as exception:
#	print type(exception).__name__,exception.args#
#	exit(1)

#with db_session:
#	h = Host(dbname="one",jobid=234)



#if __name__ == '__name__':
#	app = App()
#	app.run()
