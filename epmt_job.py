from pony.orm import *
from models import *
from sys import stdout, argv, stderr, exit
from os.path import basename
from glob import glob
import fnmatch
from os import environ
from logging import getLogger, basicConfig, DEBUG, ERROR, INFO, WARNING
import settings
logger = getLogger(__name__)  # you can use other name

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

# def lookup_or_create_metricname(metricname):
#     mn = MetricName.get(name=metricname)
#     if mn is None:
#         logger.info("Creating metricname %s",metricname)
#         mn = MetricName(name=metricname)
#     else:
#         logger.info("Found metricname %s",metricname)
#     return mn

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


# we assume tags is of the format:
#  "key1:value1 ; key2:value2"
# where the whitespace is optional and discarded. The output would be:
# { "key1": value1, "key2": value2 }
#
# We can also handle the case where a value is not set for
# a key, by assigning a default value for the key
# For example, for the input:
# "multitheaded;app=fft" and a tag_default_value="1"
# the output would be:
# { "multithreaded": "1", "app": "fft" }
#
# Note, both key and values will be strings and no attempt will be made to
# guess the type for integer/floats
def _get_tags_from_string(s, 
                          delim = settings.tag_delimiter, 
                          sep = settings.tag_kv_separator, 
                          tag_default_value = settings.tag_default_value):
    tags = {}
    for t in s.split(delim):
        t = t.strip()
        if sep in t:
            try:
                (k,v) = t.split(sep)
                k = k.strip()
                v = v.strip()
                tags[k] = v
            except Exception as e:
                logger.warning('ignoring key/value pair as it has an invalid format: {0}'.format(t))
                logger.warning("%s",e)
                continue
        else:
            # tag is not of the format k:v
            # it's probably a simple label, so use the default value for it
            tags[t] = tag_default_value
    return tags

# this assumes a list of labels like:
# ["abc", "def", "ghi"] and generates an output like:
# { "abc": "1", "def": "1", "ghi": "1" }, where the "1" comes
# from the default value of a tag
# We probably should remove this function once the job tag
# is read in as key-value pair instead of a list of comments.
def _get_tags_for_list(l, tag_default_value = settings.tag_default_value):
    tags = {}
    for t in l:
        tags[t] = tag_default_value
    return tags

# This is a generator function that will yield
# the next process dataframe from the collated file dataframe.
# It uses the numtids field to figure out where the process dataframe ends
def _get_process_df(df):
    row = 0
    nrows = df.shape[0]
    while (row < nrows):
        try:
            thr_count = int(df['numtids'][row])
        except Exception as e:
            logger.error("%s", e)
            logger.error("invalid or no value set for numtids in dataframe at index %d", row)
            return
        if (thr_count < 1):
            logger.error('invalid value({0}) set for numtids in dataframe at index {1}'.format(thr_count, row))
            return
        # now yield a dataframe from df[row ... row+thr_count]
        # make sure the yielded dataframe has it's index reset to 0
        yield df[row:row+thr_count].reset_index(drop=True)
        # advance row pointer
        row += thr_count
            

def load_process_from_pandas(df, j, u, settings):
# Assumes all processes are from same host
#	dprint("Creating process",str(df['pid'][0]),"gen",str(df['generation'][0]),"exename",df['exename'][0])
    from pandas import Timestamp

    if 'hostname' in df.columns:
        host = lookup_or_create_host(df['hostname'][0])
    else:
        host = lookup_or_create_host('unknown')

    try:
            p = Process(exename=df['exename'][0],
                        args=df['args'][0],
                        path=df['path'][0],
                        pid=int(df['pid'][0]),
                        ppid=int(df['ppid'][0]),
                        pgid=int(df['pgid'][0]),
                        sid=int(df['sid'][0]),
                        gen=int(df['generation'][0]),
                        host=host,
                        job=j,
                        user=u)
    except Exception as e:
        logger.error("%s",e)
        logger.error("Corrupted CSV or invalid input type");
        return None


    if 'exitcode' in df.columns:
        p.exitcode = int(df['exitcode'][0])

    if 'tags' in df.columns:
        tags = df['tags'][0]
        if tags:
            p.tags = _get_tags_from_string(tags)

    # remove per-process fields from the threads dataframe
    df = df.drop(labels=settings.per_process_fields, axis=1)

    # compute sums for each column, but skip ones that we know should not be summed
    thread_metric_sums = df.drop(labels=settings.skip_for_thread_metric_sums, axis=1).sum(axis=0)


    # convert the threads dataframe to a json
    # using the 'split' argument creates a json of the form:
    # { columns: ['exename', 'path', args',...], data: [['tcsh', '/bin/tcsh'..], [..]}
    # thus it preserves the column order. Remember when reading the json
    # into a dataframe, do it as:
    #
    #   df = pd.read_json(p.threads['df'], orient='split')
    #
    # where 'p' is a Process object
    #
    # Notice, that for 'metric_sums', we do not use orient='split', as
    # we save it in a flat json such as {"usetime": 1000, "systime": 200,..}
    #
    # To load the metrics sums into pandas, we would do:
    #
    #   metrics_sums = pd.read_json(p.threads['metric_sums'], typ='series')
    #
    # 
    # or you can make a Python dict, by doing:
    #
    # >>> import json
    # >>> d = json.loads(p.threads['metric_sums'])
    # >>> d
    # {u'majflt': 0, u'read_bytes': 0, u'cancelled_write_bytes': 0, u'rssmax': 28396, u'minflt': 2263, u'time_oncpu': 20528552, u'delayacct_blkio_time': 0, u'systemtime': 6998, u'invol_ctxsw': 4, u'inblock': 0, u'vol_ctxsw': 55, u'PERF_COUNT_SW_CPU_CLOCK': 2119464, u'wchar': 56, u'guest_time': 0, u'write_bytes': 0, u'timeslices': 63, u'rdtsc_duration': 2264831152, u'usertime': 11998, u'outblock': 0, u'starttime': 9792390780000, u'time_waiting': 24907, u'syscr': 266, u'rchar': 2059838, u'syscw': 7, u'processor': 13}
    # >>> d['rssmax']
    # 28396

    p.threads = { "df": df.to_json(orient='split'), "metric_sums": thread_metric_sums.to_json() }
    p.numtids = df.shape[0]

    try:
        earliest_thread_start = Timestamp(df['start'].min(), unit='us')
        latest_thread_finish = Timestamp(df['end'].max(), unit='us')
        p.start = earliest_thread_start.to_pydatetime()
        p.end = latest_thread_finish.to_pydatetime()
        p.duration = float((latest_thread_finish - earliest_thread_start).total_seconds())*float(1000000)
    except Exception as e:
        logger.error("%s",e)
        logger.error("missing or invalid value for thread start/end time");

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
                 'args':str,
                 'tags':str,
                 'hostname':str }

    # below dictionary isn't used anymore
    # dtype_dic = { 
    #     'pid':                        float,
    #     'generation':                 float,
    #     'ppid':                       float,
    #     'pgid':                       float,
    #     'sid':                        float,
    #     'numtids':                    float }

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
    all_tags = set([])
    all_procs = []

    for hostname, files in filedict.iteritems():
        # logger.debug("Processing host %s",hostname)
        # h = lookup_or_create_host(hostname)
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
            if comment:
# Merge all tags into one list for job
                all_tags.add(comment)

            if tarfile:
                info = tarfile.getmember(f)
                flo = tarfile.extractfile(info)
            else:
                flo = f
                
            from pandas import read_csv
            collated_df = read_csv(flo,
                                   sep=",",
#                                   dtype=dtype_dic, 
                                   converters=conv_dic,
                                   skiprows=rows, escapechar='\\')
            if collated_df.empty:
                logger.error("Something wrong with file %s, readcsv returned empty, skipping...",f)
                continue

# Make Process/Thread/Metrics objects in DB
            # there are 1 or more process dataframes in the collated df
            # let's iterate over them
            for df in _get_process_df(collated_df):
                p = load_process_from_pandas(df, j, u, settings)
                if not p:
                    logger.error("Failed loading from pandas, file %s!",f);
                    continue
                all_procs.append(p)
# Compute duration of job
                if (p.start < earliest_process):
                    earliest_process = p.start
                if (p.end > latest_process):
                    latest_process = p.end
# Debugging/    progress
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
        # once the tags becomes a string of key/value pairs, then
        # just use _get_tags_from_string instead of _get_tags_for_list
        j.tags = _get_tags_for_list(all_tags)
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
    logger.info("Staged import of %d processes", len(j.processes))
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

