#!/usr/bin/env python
import settings
from pony.orm import *
from models import *
from sys import stdout, argv, stderr
# from pytz import UTC
# from pytz import timezone
from pandas import read_csv,Timestamp
from os.path import basename
from glob import glob
from itertools import cycle
from logging import getLogger, basicConfig, DEBUG, ERROR, INFO, WARNING

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
def lookup_or_create_job(jobid,user,metadata={}):
	job = Job.get(jobid=jobid)
	if job is None:
		logger.debug("Creating job %s",jobid)
		job = Job(jobid=jobid,user=user)
                if metadata:
                    assert metadata['job_pl_id'] == jobid
                    job.jobname = metadata['job_pl_jobname']
                    job.jobscriptname = metadata['job_pl_scriptname']
                    job.exitcode = metadata['job_el_status']
# fix below
                    job.env_dict = metadata['job_pl_env']
                    job.info_dict = metadata['job_pl_from_batch'] # end batch also
##	metadata['job_pl_id'] = global_job_id
##	metadata['job_pl_scriptname'] = global_job_scriptname
##	metadata['job_pl_jobname'] = global_job_name
##	metadata['job_pl_from_batch'] = from_batch
#	metadata['job_pl_hostname'] = gethostname()
#	metadata['job_pl_username'] = global_job_username
#	metadata['job_pl_groupnames'] = global_job_groupnames
#	metadata['job_pl_env_len'] = len(env)
#	metadata['job_pl_env'] = env
#	metadata['job_pl_submit'] = datetime.now()
#	metadata['job_pl_start'] = ts
#	metadata['job_el_env_changes_len'] = len(env)
#	metadata['job_el_env_changes'] = env
#	metadata['job_el_stop'] = ts
#	metadata['job_el_from_batch'] = from_batch
#	metadata['job_el_status'] = status
                    
	return job

@db_session
def lookup_or_create_host(hostname):
	host = Host.get(name=hostname)
	if host is None:
		logger.debug("Creating host %s",hostname)
		host = Host(name=hostname)
	return host

@db_session
def lookup_or_create_user(username):
	user = User.get(name=username)
	if user is None:
		logger.debug("Creating user %s",username)
		user = User(name=username)
	return user

@db_session
def lookup_or_create_group(groupname):
	group = Group.get(name=groupname)
	if group is None:
		logger.debug("Creating group %s",groupname)
		group = Group(name=groupname)
	return group

@db_session
def lookup_or_create_tags(tagnames):
    retval=[]
    for tagname in tagnames:
	tag = Tag.get(name=tagname)
	if tag is None:
            logger.debug("Creating tag %s",tagname)
            tag = Tag(name=tagname)
        retval.append(tag)
    return retval

@db_session
def lookup_or_create_queue(queuename):
	queue = Queue.get(name=queuename)
	if queue is None:
		logger.debug("Creating queue %s",queuename)
		queue = Queue(name=queuename)
	return queue
@db_session
def lookup_or_create_account(accountname):
	account = account.get(name=accountname)
	if account is None:
		logger.debug("Creating account %s",accountname)
		account = account(name=accountname)
	return account

@db_session
def load_process_from_pandas(df, h, j, u, tags, mns):
# Assumes all processes are from same host
#	dprint("Creating process",str(df['pid'][0]),"gen",str(df['generation'][0]),"exename",df['exename'][0])
	earliest_thread = datetime.datetime.utcnow()
	latest_thread = datetime.datetime.fromtimestamp(0)

	try:
            p = Process(exename=df['exename'][0],
                        args=df['args'][0],
                        path=df['path'][0],
                        pid=int(df['pid'][0]),
                        ppid=int(df['ppid'][0]),
                        pgid=int(df['pgid'][0]),
                        sid=int(df['sid'][0]),
                        gen=int(df['generation'][0]),
                        job=j,
                        host=h,
                        user=u)
        except ValueError:
            logger.error("Data conversion error, likely corrupted CSV");
            return None

# Add tags to process and job        
        for t in tags:
            p.tags.add(t)
            j.tags.add(t)

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
		for metricname,obj in mns.iteritems():
                    value = row.get(metricname)
                    if value is None:
                        logger.error("Key %s not found in data",metricname)
                        return None
                    m = Metric(metricname=obj,value=value,thread=t)
                    t.metrics.add(m)
		p.threads.add(t)

        
	p.start = earliest_thread
	p.end = latest_thread
	p.duration = int(float((latest_thread - earliest_thread).total_seconds())*float(1000000))
#	print "Earliest thread start:",earliest_thread,"\n","Latest thread end:",latest_thread,"\n","Computed duration of process:",(p.end-p.start).total_seconds(),"seconds","\n","Duration of process:",p.duration,"microseconds"
	return p

#
# Extract a dictionary from the rows of header on the file
#

def extract_header_dict(jobdatafile,comment="#"):
    rows=0
    header_dict={}
    with open(jobdatafile,'r') as file:
        for line in file:
            line = line.strip()
            if line.startswith(comment):
                rows += 1
# We could extend this here to support multiple tags                
                header_dict["tags"]=[ line[1:].lstrip() ]
    logger.debug("%d rows of header, dictionary is %s",rows,header_dict)
    return rows,header_dict

#
# Load the entire job into the DB, consisting of a job_metadata file and a dir of papiex files
#

def ETL_job_dir(jobid, dir, metadata, pattern=settings.input_pattern):
    if not dir.endswith("/"):
        logger.warn("%s should have a trailing /",dir)
        dir = dir+"/"
    filedict = get_filedict(dir,pattern)
    return(ETL_job_dict(metadata,filedict))

@db_session
def ETL_job_dict(metadata, filedict):
# Only fields used for now
    jobid = metadata['job_pl_id']
    username = metadata['job_pl_username']
#
    logger.info("Processing job id %s",jobid)
    hostname = ""
    file = ""
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
    then = datetime.datetime.now()
    csvt = datetime.timedelta()
    ponyt = datetime.timedelta()
    earliest_process = datetime.datetime.utcnow()
    latest_process = datetime.datetime.fromtimestamp(0)
    stdout.write('-')
# Hostname, job, metricname objects
# Iterate over hosts
    logger.debug("Iterating over hosts for job ID %s: %s",jobid,filedict.keys())
    u = lookup_or_create_user(username)
    j = lookup_or_create_job(jobid,u,metadata)
    mns = {}
    for hostname, files in filedict.iteritems():
        logger.debug("Processing host %s",hostname)
        h = lookup_or_create_host(hostname)
        cntmax = len(files)
        cnt = 0
	for f in files:
            logger.debug("Processing file %s",f)
#
            stdout.write('\b')            # erase the last written char
            stdout.write(spinner.next())  # write the next character
            stdout.flush()                # flush stdout buffer (actual character display)
#
            rows,header = extract_header_dict(f)
            tags = lookup_or_create_tags(header['tags'])

            csv = datetime.datetime.now()
            pf = read_csv(f,
                          sep=",",
#                          dtype=dtype_dic, 
                          converters=conv_dic,
                          skiprows=rows)
#            print pf["path"],pf["args"]
            csvt += datetime.datetime.now() - csv

            if pf.empty:
                logger.error("Something wrong with file %s, readcsv returned empty, skipping...",f)
                continue

# Lookup or create the necessary objects, only happens once!
            if not mns:
                for metric in pf.columns[settings.metrics_offset:].values.tolist():
                    logger.info("Creating metric %s",metric)
                    mns[metric] = lookup_or_create_metricname(metric)
#
            pony = datetime.datetime.now()
            p = load_process_from_pandas(pf, h, j, u, tags, mns)
            ponyt += datetime.datetime.now() - pony
            if not p:
                logger.error("Failed loading from pandas, file %s!",f);
                continue

            if (p.start < earliest_process):
                earliest_process = p.start
            if (p.end > latest_process):
                latest_process = p.end

#
#
#
            j.processes.add(p)
            cnt += 1
            if cntmax/100 != 0:
                if cnt % (cntmax/100) == 0:
                    logger.info("Did %d of %d...",cnt,cntmax)
#
#
#

    j.start = earliest_process
    j.end = latest_process
    d = j.end - j.start
    j.duration = int(d.total_seconds()*1000000)
#
#
#
    stdout.write('\b')            # erase the last written char
    logger.info("Earliest process start: %s",j.start)
    logger.info("Latest process end: %s",j.end)
    logger.info("Computed duration of job: %f us, %.2f m",j.duration,j.duration/60000000)
    logger.info("%d processes imported", len(j.processes))
    logger.info("%f processes per second",len(j.processes)/float((datetime.datetime.now() - then).total_seconds()))
    logger.info("Import took %s seconds",datetime.datetime.now() - then)
    logger.info("load_process_from_pandas() took %s", ponyt)
    logger.info("read_csv took %s",csvt)
    logger.info(j)
    return j

def get_filedict(dirname,pattern=settings.input_pattern):
    # Now get all the files in the dir
    files = glob(dirname+pattern)
    if not files:
        logger.error("%s matched no files",dirname+pattern);
        exit(1);
    logger.debug("%d files to submit",len(files))
    if (len(files) > 30):
        logger.debug("Skipping printing files, too many")
    else:
        logger.debug("%s",files)
    # Build a hash of hosts and their data files
    filedict={}
    dumperr = False
    for f in files:
        t = basename(f)
        ts = t.split("papiex")
        if len(ts) == 2:
            if len(ts[0]) == 0:
                host = "unknown"
                dumperr = True
            else:
                host = ts[0]
        else:
            logger.warn("Split failed of %s, only %d parts",t,len(ts))
            continue
        if filedict.get(host):
            filedict[host].append(f)
        else:
            filedict[host] = [ f ]
    if dumperr:
        logger.warn("Host not found in name split, using unknown host")

    return filedict


#
#
#
if (__name__ == "__main__"):
    import argparse
    parser=argparse.ArgumentParser(description="...")
    parser.add_argument('jobid',nargs="?",type=int,help="directory containing the job_metadata file for the job");
    parser.add_argument('data_dir',nargs="?",type=str,help="directory of papiex output files for the job");
    parser.add_argument('metadata_dir',nargs="?",type=str,help="directory containing the job_metadata file for the job");
    parser.add_argument('--drop',action='store_true',help="Drop all tables first")
    parser.add_argument('--debug',action='store_true',help="Debug mode, be verbose")
    parser.add_argument('--test',action='store_true',help="Test mode, job id 4, requires data and metadata in ./test-job")
#    parser.add_argument("-v", "--verbosity", action="count",
#                        help="increase output verbosity")
# parser.add_argument("-v", "--verbosity", type=int, choices=[0, 1, 2],
#                    help="increase output verbosity")
    args = parser.parse_args()
    if args.debug:
        basicConfig(level=DEBUG)
    else:
        basicConfig(level=INFO)
    # "./sample-data/"

    logger.info("Using DB: %s", settings.db_params)
    db.bind(**settings.db_params)
    db.generate_mapping(create_tables=True)
    if args.drop:
        db.drop_all_tables(with_all_data=True)
    db.create_tables()

    from epmt_cmds import read_job_metadata
    if args.test:
        metadata = read_job_metadata("./test-job/job_metadata")
        metadata['job_pl_id'] = 4
        logger.warning("Forcing job id to be %s for test",4)
        j = ETL_job_dir(4,"./test-job/",metadata)
    elif args.jobid and args.data_dir and args.metadata_dir:
        metadata = read_job_metadata(args.metadata_dir+"/job_metadata")
        if (metadata['job_pl_id'] != args.jobid):
            logger.warning("Forcing job id to be %s from command line",args.jobid)
            metadata['job_pl_id'] = args.jobid
        j = ETL_job_dir(args.jobid,args.data_dir,metadata)
    else:
        parser.print_help(stderr)
        metadata = read_job_metadata("./test-job/job_metadata")
        j = None

    if j:
	exit(0)
    else:
	exit(1)
else:
    logger.info("Using DB: %s", settings.db_params)
    db.bind(**settings.db_params)
    db.generate_mapping(create_tables=True)
    db.drop_all_tables(with_all_data=True)
    db.create_tables()
