#!/usr/bin/env python
import settings
from pony.orm import *
from models import *
from os.path import basename
from sys import stdout, argv
# from pytz import UTC
# from pytz import timezone
from pandas import read_csv,Timestamp
from glob import glob
from itertools import cycle
from logging import getLogger, basicConfig, DEBUG, ERROR
logger = getLogger(__name__)  # you can use other name
#
#
# Spinning cursor sequence
spinner = cycle(['-', '/', '|', '\\'])

# Construct a number from the pattern

def sortKeyFunc(s):
    t = basename(s)
# if this changes we must adjust this
#    assert settings.input_pattern == "papiex-[0-9]*-[0-9]*.csv"
# skip papiex- and .csv
    t = t[7:-4]
# append instance number 
    t2 = t.split("-")
    return int(t2[0]+t2[1])

@db_session
def lookup_or_create_metricname(metricname):
	mn = MetricName.get(name=metricname)
	if mn is None:
		logger.debug("Creating metric %s",metricname)
		mn = MetricName(name=metricname)
	return mn

@db_session
def lookup_or_create_job(jobid):
	job = Job.get(jobid=jobid)
	if job is None:
		logger.debug("Creating job %s",jobid)
		job = Job(jobid=jobid)
	return job

@db_session
def lookup_or_create_host(hostname):
	host = Host.get(name=hostname)
	if host is None:
		logger.debug("Creating host %s",hostname)
		host = Host(name=hostname)
	return host

@db_session
def load_process_from_pandas(df, h, j, mns):
# Assumes all processes are from same host
#	dprint("Creating process",str(df['pid'][0]),"gen",str(df['generation'][0]),"exename",df['exename'][0])
	earliest_thread = datetime.datetime.utcnow()
	latest_thread = datetime.datetime.fromtimestamp(0)

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
	# Add all threads
	for index, row in df.iterrows():
#		dprint "Adding thread TID: "+str(row['tid']),row['start']
#		print index,row['start']
#		start = datetime.datetime.utcfromtimestamp(row['start'])
		start = Timestamp(row['start'], unit='us')
		if (start < earliest_thread):
			earliest_thread = start
#		start = start.tz_localize(UTC)
		end = Timestamp(row['end'], unit='us')
		if (end > latest_thread):
			latest_thread = end
#		end = end.tz_localize(UTC)
		duration = end-start
#		dprint("Creating thread",str(row['tid']),"start",start,"end",end,"duration",duration)
		t = Thread(tid=row['tid'],
			   start=start,
			   end=end,
			   duration=int(float(duration.total_seconds())*float(1000000)),
			   process=p)
		for metric,obj in mns.iteritems():
#			dprint("Creating metric",metric,"value",df[metric][0])
			m = Metric(metricname=obj,value=df[metric][0],thread=t)
			t.metrics.add(m)
		p.threads.add(t)

	p.start = earliest_thread
	p.end = latest_thread
	p.duration = int(float((latest_thread - earliest_thread).total_seconds())*float(1000000))
#	print "Earliest thread start:",earliest_thread,"\n","Latest thread end:",latest_thread,"\n","Computed duration of process:",(p.end-p.start).total_seconds(),"seconds","\n","Duration of process:",p.duration,"microseconds"
	return p

@db_session
def load_job_from_dirofcsvs(jobid, hostname, pattern=settings.input_pattern, dirname="./sample-data/"):
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
#	files = [ "sample-output/papiex-24414-0.csv" ]
	files = sorted(glob(dirname+pattern),key=sortKeyFunc)
	if not files:
		stdout.write(dirname+pattern+" matched no files.\n");
		return None
# Sort by PID
	then = datetime.datetime.now()
	csvt = datetime.timedelta()
	ponyt = datetime.timedelta()
	earliest_process = datetime.datetime.utcnow()
	latest_process = datetime.datetime.fromtimestamp(0)
	stdout.write('-')
# Hostname, job, metricname objects
	h = None
	m = None
	mns = {}
# Iterate over files 
	logger.debug("%d files matched (%s): %s",len(files),dirname+pattern,files)
	for f in files:
		stdout.write('\b')            # erase the last written char
		stdout.write(spinner.next())  # write the next character
		stdout.flush()                # flush stdout buffer (actual character display)
		csv = datetime.datetime.now()
	        pf = read_csv(f,
				 dtype=dtype_dic, 
				 converters=conv_dic,
			         comment="#",
			         skiprows=1)
		csvt += datetime.datetime.now() - csv
# Lookup or create the necessary objects, only happens once!
		if h is None:
			for metric in pf.columns[settings.metrics_offset:].values.tolist():
				mns[metric] = lookup_or_create_metricname(metric)
			j = lookup_or_create_job(jobid)
			h = lookup_or_create_host(hostname)
		pony = datetime.datetime.now()
		p = load_process_from_pandas(pf, h, j, mns)
		if (p.start < earliest_process):
			earliest_process = p.start
		if (p.end > latest_process):
			latest_process = p.end
		ponyt += datetime.datetime.now() - pony
#
#
#
	j.processes.add(p)
	j.start = earliest_process
	j.end = latest_process
	j.duration = int(float((latest_process - earliest_process).total_seconds())*float(1000000))
#
#
#
	stdout.write('\b')            # erase the last written char
	logger.info("Earliest process start: %s",earliest_process)
	logger.info("Latest process end: %s",latest_process)
	logger.info("Computed duration of job: %f",(j.end-j.start).total_seconds())
	logger.info("Duration of job: %f",j.duration)
	logger.info("%d files imported", len(files))
	logger.info("%s seconds",datetime.datetime.now() - then)
	logger.info("%f per second",len(files)/float((datetime.datetime.now() - then).total_seconds()))
	logger.info("load_process_from_pandas() took %s", ponyt)
	logger.info("read_csv took %s",csvt)
	logger.info(j)
	return j

#
#
#
basicConfig(level=DEBUG)
#
#
#
if settings.db_params.get('hostname'):
	logger.info("Using DB: %s %s %s",settings.db_params['provider'],"Hostname:",settings.db_params['provider'])
else:
	logger.info("Using DB: %s", settings.db_params['provider'])
db.bind(**settings.db_params)
db.generate_mapping(create_tables=True)
db.drop_all_tables(with_all_data=True)
db.create_tables()
#
#
#
j = load_job_from_dirofcsvs(4,"hostname.foo.com",dirname="./sample-data/")
if j:
	exit(0)
else:
	exit(1)