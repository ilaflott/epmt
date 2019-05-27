from pony.orm import *
from models import *
from sys import stdout, argv, stderr, exit
from os.path import basename
from glob import glob
import fnmatch
from os import environ
from logging import getLogger, basicConfig, DEBUG, ERROR, INFO, WARNING
logger = getLogger(__name__)  # you can use other name

#
#
# Spinning cursor sequence
#from itertools import cycle
#spinner = cycle(['-', '/', '|', '\\'])

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

def lookup_or_create_metricname(metricname):
    mn = MetricName.get(name=metricname)
    if mn is None:
        logger.info("Creating metricname %s",metricname)
        mn = MetricName(name=metricname)
    else:
        logger.info("Found metricname %s",metricname)
    return mn

def create_job(jobid,user,metadata={}):
    job = Job.get(jobid=jobid)
    if job is None:
        logger.info("Creating job %s",jobid)
        job = Job(jobid=jobid,user=user)
        if metadata:
            if metadata['job_pl_id'] != jobid:
                logger.warning("metadata job id did not match job id %s vs %s, continuing anyways...",metadata['job_pl_id'],jobid)
            job.jobname = metadata['job_pl_jobname']
            job.jobscriptname = metadata['job_pl_scriptname']
            job.exitcode = metadata['job_el_status']
# fix below
            job.env_dict = metadata['job_pl_env']
            job.env_changes_dict = metadata['job_el_env_changes']
            job.info_dict = metadata['job_pl_from_batch'] # end batch also
        return job
    else:
        logger.error("Job %s (at %s) is already in the database",job.jobid,job.start)
        return None

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
                    

def lookup_or_create_host(hostname):
    host = Host.get(name=hostname)
    if host is None:
        logger.info("Creating host %s",hostname)
        host = Host(name=hostname)
    else:
        logger.debug("Found host %s",hostname)
    return host

def lookup_or_create_user(username):
    user = User.get(name=username)
    if user is None:
        logger.info("Creating user %s",username)
        user = User(name=username)
    else:
        logger.debug("Found user %s",username)
    return user

def lookup_or_create_tags(tagnames):
    retval=[]
    for tagname in tagnames:
        tag = Tag.get(name=tagname)
        if tag is None:
            logger.info("Creating tag %s",tagname)
            tag = Tag(name=tagname)
        else:
            logger.debug("Found tag %s",tagname)
        retval.append(tag)
    return retval

def load_process_from_pandas(df, h, j, u, tags, mns):
# Assumes all processes are from same host
#	dprint("Creating process",str(df['pid'][0]),"gen",str(df['generation'][0]),"exename",df['exename'][0])
    from pandas import Timestamp

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
    except Exception as e:
        logger.error("%s",e)
        logger.error("Corrupted CSV or invalid input type");
        return None

# Add all threads in process
    threads = []
    for index, row in df.iterrows():
# Add Thread to process
        start = Timestamp(row['start'], unit='us')
        end = Timestamp(row['end'], unit='us')
        duration = end-start
        t = Thread(tid=row['tid'],start=start,end=end,duration=float(duration.total_seconds())*float(1000000),process=p)
        if t is None:
            logger.error("Thread duration error, likely corrupted CSV");
            return None
        threads.append(t)
# Add Metrics to thread
        # metrics = []
        # for metricname,obj in mns.iteritems():
        #     value = row.get(metricname)
        #     if value is None:
        #         logger.error("Key %s not found in data",metricname)
        #         return None
        #     m = Metric(metricname=obj,value=value,thread=t)
        #     metrics.append(m)
        #     t.metrics.add(metrics)
        metrics = {}
        for metricname in mns:
            value = row.get(metricname)
            if value is None:
                logger.error("Key %s not found in data",metricname)
                return None
            metrics[metricname] = value
        t.metrics = metrics

# Compute wallclock duration for job from threads
        if (start < earliest_thread):
            earliest_thread = start
        if (end > latest_thread):
            latest_thread = end
# Record tags, threads, start, end, wall clock duration for process
    if tags:
        p.tags.add(tags)
    p.threads.add(threads)
    p.start = earliest_thread
    p.end = latest_thread
    p.duration = float((latest_thread - earliest_thread).total_seconds())*float(1000000)
#	print "Earliest thread start:",earliest_thread,"\n","Latest thread end:",latest_thread,"\n","Computed duration of process:",(p.end-p.start).total_seconds(),"seconds","\n","Duration of process:",p.duration,"microseconds"
    return p
    
#
# Extract a dictionary from the rows of header on the file
#

def extract_tags_from_comment_line(jobdatafile,comment="#",tarfile=None):
    rows=0
    if tarfile:
        try:
            info = tarfile.getmember(jobdatafile)
        except KeyError:
            logger.error('BUG: Did not find %s in tar archive' % str(tarfile))
            exit(1)
        else:
            file = tarfile.extractfile(info)
    else:
        file = open(jobdatafile,'r')
    
    line = file.readline().strip()
    if line.startswith(comment):
        rows += 1
        return rows, line[1:].lstrip()

    return rows, None

#        for member in tar.getmembers():

#def check_experiment_in_metadata(metadata):
#    for i in ("exp_name","exp_component","exp_oname","exp_jobname"):
#        if i not in metadata:
#            return False
#    return True
#
# Load experiment
# 
@db_session
def ETL_ppr(metadata, jobid):
#    if not check_experiment_in_metadata(metadata):
#        return None

    logger.info("Creating PostProcessRun(%s,%s,%s,%s)",
                metadata["exp_component"],
                metadata["exp_name"],
                metadata["exp_jobname"],
                metadata["exp_oname"])
    exp = PostProcessRun(component=metadata["exp_component"],
                         name=metadata["exp_name"],
                         jobname=metadata["exp_jobname"],
                         oname=metadata["exp_oname"],
                         user=Job[jobid].user,
                         job=Job[jobid])
    return exp

@db_session
def ETL_job_dict(metadata, filedict, settings, tarfile=None):
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

    standards = [ "exename","path","args","pid","generation","ppid","pgid","sid","numtids","tid","start","end" ]

    then = datetime.datetime.now()
    csvt = datetime.timedelta()
    earliest_process = datetime.datetime.utcnow()
    latest_process = datetime.datetime.fromtimestamp(0)
#    stdout.write('-')
# Hostname, job, metricname objects
# Iterate over hosts
    logger.debug("Iterating over %d hosts for job ID %s, user %s...",len(filedict.keys()),jobid,username)
    u = lookup_or_create_user(username)
    j = create_job(jobid,u,metadata)
    if not j:
# We might have leaked a username to the database here
# FIX!        
        return None

    didsomething = False
    oldcomment = None
    mns = []
    tags = []
    all_tags = []
    all_procs = []

    for hostname, files in filedict.iteritems():
        logger.debug("Processing host %s",hostname)
        h = lookup_or_create_host(hostname)
        cntmax = len(files)
        cnt = 0
        for f in files:
            logger.debug("Processing file %s",f)
#
#            stdout.write('\b')            # erase the last written char
#            stdout.write(spinner.next())  # write the next character
#            stdout.flush()                # flush stdout buffer (actual character display)
#
            csv = datetime.datetime.now()
            rows,comment = extract_tags_from_comment_line(f,tarfile=tarfile)
# Check comment/tags cache
            if comment and comment != oldcomment:
                logger.info("Missed tag cache %s",comment)
                tags = lookup_or_create_tags([comment])
                oldcomment = comment
# Merge all tags into one list for job
                all_tags = list(set().union(all_tags,tags))

            if tarfile:
                info = tarfile.getmember(f)
                flo = tarfile.extractfile(info)
            else:
                flo = f
                
            from pandas import read_csv
            pf = read_csv(flo,
                          sep=",",
#                          dtype=dtype_dic, 
                          converters=conv_dic,
                          skiprows=rows, escapechar='\\')
            if pf.empty:
                logger.error("Something wrong with file %s, readcsv returned empty, skipping...",f)
                continue

# Lookup or create the necessary objects, only happens once!
            if not mns:
                # for metric in pf.columns[settings.metrics_offset:].values.tolist():
                #     mns[metric] = lookup_or_create_metricname(metric)
                mns = pf.columns[settings.metrics_offset:].values.tolist()
# Make Process/Thread/Metrics objects in DB
            p = load_process_from_pandas(pf, h, j, u, tags, mns)
            if not p:
                logger.error("Failed loading from pandas, file %s!",f);
                continue
            all_procs.append(p)
# Compute duration of job
            if (p.start < earliest_process):
                earliest_process = p.start
            if (p.end > latest_process):
                latest_process = p.end
# Debugging/progress
            cnt += 1
            csvt += datetime.datetime.now() - csv
            if cnt % 1000 == 0:
                    logger.info("Did %d of %d...%.2f/sec",cnt,cntmax,cnt/csvt.total_seconds())
#
        if cnt:
            didsomething = True

#    stdout.write('\b')            # erase the last written char

    if filedict:
        if not didsomething:
            logger.warning("Something went wrong in parsing CSV files")
            return False
    else:
        logger.warning("Submitting job with no CSV data")

# Add sum of tags to job        
    if all_tags:
        logger.info("Adding %d tags to job",len(all_tags))
        j.tags.add(all_tags)
# Add all processes to job
    if all_procs:
        logger.info("Adding %d processes to job",len(all_procs))
        j.processes.add(all_procs)
# Update start/end/duration of job
#       j.start = earliest_process
#        j.end = latest_process
#
#
#
    j.start = metadata["job_pl_start"]
    j.end = metadata["job_el_stop"]
    d = j.end - j.start
    j.duration = int(d.total_seconds()*1000000)
    
#
#
#
    logger.info("Earliest process start: %s",j.start)
    logger.info("Latest process end: %s",j.end)
    logger.info("Computed duration of job: %f us, %.2f m",j.duration,j.duration/60000000)
    now = datetime.datetime.now() 
    logger.info("Staged import of %d processes, %d threads", 
                len(j.processes),len(j.processes.threads))
    logger.info("Staged import took %s, %f processes per second",
                now - then,len(j.processes)/float((now-then).total_seconds()))
                
    return j

def setup_orm_db(settings,drop=False,create=True):
    logger.info("Binding to DB: %s", settings.db_params)
    try:
        db.bind(**settings.db_params)
    except Exception as e:
        if (type(e).__name__ == "BindingError"):
            pass
        else:
            logger.error("Binding to DB, check database existance and connection parameters")
            logger.error("Exception(%s): %s",type(e).__name__,str(e).strip())
            return False

    try:
        logger.info("Generating mapping from schema...")
        db.generate_mapping(create_tables=True)
    except Exception as e:
        if (type(e).__name__ == "BindingError"):
            pass
        else:
            logger.error("Mapping to DB, did the schema change? Perhaps drop and create?")
            logger.error("Exception(%s): %s",type(e).__name__,str(e).strip())
            return False
        
    if drop:
        logger.warning("DROPPING ALL DATA AND TABLES!")
        db.drop_all_tables(with_all_data=True)
        db.create_tables()
    return True

#
#
#
if (__name__ == "__main__"):
    import argparse
    from epmt_cmds import read_job_metadata, dump_settings

    parser=argparse.ArgumentParser(description="Load a job into the database.\nDetailed configuration is stored in settings.py.")

    parser.add_argument('data_dir',type=str,help="Directory containing papiex data files with pattern: "+settings.input_pattern);
    parser.add_argument('metadata_dir',nargs="?",type=str,help="Directory containing the job_metadata file, defaults to data_dir");
    parser.add_argument('jobid',type=str,nargs="?",help="Job id, a unique integer, should match that in job_metadata file");
    parser.add_argument('-d', '--debug',action='count',help="Increase level of verbosity/debug")
    parser.add_argument('--drop',action='store_true',help="Drop all tables/data and recreate before import")
    parser.add_argument('-f', '--force',action='store_true',help="Override job id in job_metadata file")
    parser.add_argument('-n', '--dry-run',action='store_true',help="Don't touch the database");

#    parser.add_argument("-v", "--verbosity", action="count",
#                        help="increase output verbosity")
# parser.add_argument("-v", "--verbosity", type=int, choices=[0, 1, 2],
#                    help="increase output verbosity")
    args = parser.parse_args()

    if not args.debug:
        basicConfig(level=WARNING)
    elif args.debug == 1:
        basicConfig(level=INFO)
    elif args.debug >= 2:
        basicConfig(level=DEBUG)

    if args.dry_run and args.drop:
        logger.warning("Dry-run will still drop tables, hope you know what you are doing!")

    if not args.data_dir.endswith("/"):
        logger.warn("data_dir %s should have a trailing /",args.data_dir)
        args.data_dir = args.data_dir+"/"

    if args.data_dir and not args.metadata_dir:
        logger.info("Assuming metadata_dir is data_dir %s",args.data_dir)
        args.metadata_dir = args.data_dir
    elif not args.metadata_dir.endswith("/"):
        logger.warn("metadata_dir %s should have a trailing /",args.metadata_dir)
        args.metadata_dir = args.metadata_dir+"/"

    metadata = read_job_metadata(args.metadata_dir+"job_metadata")

    if not args.jobid:
        args.jobid = metadata['job_pl_id']
    elif args.jobid != metadata['job_pl_id']:
        if not args.force:
            logger.error("Job id in metadata %s different from %s on command line, see --force",metadata['job_pl_id'],args.jobid)
            exit(1)
        else:
            logger.warning("Forcing job id to be %s from command line",args.jobid)
            metadata['job_pl_id'] = args.jobid

    if setup_orm_db(args.drop) == False:
        exit(1)

    if args.dry_run:
        logger.info("Skipping ETL...")
    else:
        j = ETL_job_dir(args.jobid,args.data_dir,metadata)
        if not j:
            exit(1)
    exit(0)

