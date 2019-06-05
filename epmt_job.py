from pony.orm import *
from models import *
from sys import stdout, argv, stderr, exit
from os.path import basename
from glob import glob
import fnmatch
from os import environ
from logging import getLogger, basicConfig, DEBUG, ERROR, INFO, WARNING
import settings
from os import getuid
from pwd import getpwnam, getpwuid
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

def create_job(jobid,user):
    job = Job.get(jobid=jobid)
    if job is None:
        logger.info("Creating job %s",jobid)
        job = Job(jobid=jobid,user=user)
    else:
        logger.error("Job %s (at %s) is already in the database",job.jobid,job.start)
        return None
    return job

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
    if not s or len(s) == 0:
        return None
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
#def _get_tags_for_list(l, tag_default_value = settings.tag_default_value):
#    tags = {}
#    for t in l:
#        tags[t] = tag_default_value
#    return tags

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
            

def load_process_from_pandas(df, h, j, u, settings):
# Assumes all processes are from same host
#	dprint("Creating process",str(df['pid'][0]),"gen",str(df['generation'][0]),"exename",df['exename'][0])
    from pandas import Timestamp

    if 'hostname' in df.columns:
        host = lookup_or_create_host(df['hostname'][0])
    else:
        # fallback to the host read from the filename
        host = lookup_or_create_host(h)

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
    df = df.drop(labels=settings.per_process_fields, axis=1, errors = 'ignore')

    # compute sums for each column, but skip ones that we know should not be summed
    # we then convert the pandas series of sums to a Python dict
    thread_metric_sums = df.drop(labels=settings.skip_for_thread_metric_sums, axis=1).sum(axis=0).to_dict()
    # we add a composite metric comprising of user+system time as this
    # is needed in queries, and Pony doesn't allow operations on json fields
    # in a Query
    # TODO: can this be removed?
    thread_metric_sums['user+system'] = thread_metric_sums.get('usertime', 0) + thread_metric_sums.get('systemtime', 0)


    # convert the threads dataframe to a json
    # using the 'split' argument creates a json of the form:
    # { columns: ['exename', 'path', args',...], data: [['tcsh', '/bin/tcsh'..], [..]}
    # thus it preserves the column order. Remember when reading the json
    # into a dataframe, do it as:
    #
    #   df = pd.read_json(p.threads_df, orient='split')
    #
    # where 'p' is a Process object
    #
    # We pass metric_sums as a python dictionary to Pony so we can do
    # complex queries in Pony using metrics in the 'metric_sums' dict.
    #

    p.threads_df = df.to_json(orient='split')
    p.threads_sums = thread_metric_sums
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

    logger.debug("Earliest thread start: %s, Latest thread end: %s",str(earliest_thread_start),str(latest_thread_finish))
    logger.debug("Process wallclock: %s, Computed process wallclock: %s s.",str(p.duration),str((p.end-p.start).total_seconds()))
    return p
    
#
# Extract a dictionary from the rows of header on the file
#

def extract_tags_from_comment_line(jobdatafile,comment="#",tarfile=None):
    rows = 0
    retstr = None

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
    
    line = file.readline()
    while line:
        line = line.strip()
        if len(line) == 0 or line.startswith(comment):
            if rows == 0:
                retstr = line[1:].lstrip()
            rows += 1
            line = file.readline()
        else:
            return rows, retstr

    return rows, retstr

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

# walk up the process tree starting from the supplied ancestor
# and ensure  that every ancestor of the supplied process(proc) includes
# proc in its descendants, and proc.ancestors includes all ancestors
def _proc_ancestors(pid_map, proc, ancestor_pid):
    if ancestor_pid in pid_map:
        ancestor = pid_map[ancestor_pid]
        ancestor.descendants.add(proc)
        proc.ancestors.add(ancestor)
        # now that we have done this node let's go to its parent
        _proc_ancestors(pid_map, proc, ancestor.ppid)


def _create_process_tree(pid_map):
    logger.debug("creating process tree...")
    for (pid, proc) in pid_map.items():
        ppid = proc.ppid
        if ppid in pid_map:
            parent = pid_map[ppid]
            proc.parent = parent
            parent.children.add(proc)
    logger.debug("done connecting parent/child processes")
    for (pid, proc) in pid_map.items():
        ppid = proc.ppid
        _proc_ancestors(pid_map, proc, ppid)
    logger.debug("process tree created")

# This function takes as input raw metadata from the start/stop and produces
# extended dictionary of additional fields used in the ETL. This created
# structure is never stored and just used for information exchange

# The following raw fields are stored during start/stop
#    metadata['job_pl_id'] = jobid
#    metadata['job_pl_hostname'] = gethostname()
#    metadata['job_pl_start_ts'] = ts
#    metadata['job_pl_submit_ts'] = submit_ts
#    metadata['job_pl_env'] = start_env
#    metadata['job_el_env'] = stop_env
#    metadata['job_el_stop_ts'] = ts
#    metadata['job_el_from_batch'] = from_batch
#    metadata['job_el_exitcode'] = exitcode
#    metadata['job_el_reason'] = reason

def get_batch_envvar(var,where):
# Torque
# http://docs.adaptivecomputing.com/torque/4-1-7/Content/topics/2-jobs/exportedBatchEnvVar.htm
    key2pbs = {
        "JOB_NAME":"PBS_JOBNAME",
        "JOB_USER":"PBS_O_LOGNAME"
        }
# Slurm
# http://hpcc.umd.edu/hpcc/help/slurmenv.html
    key2slurm = {
        "JOB_NAME":"SLURM_JOB_NAME", 
        "JOB_USER":"SLURM_JOB_USER"
        }

    logger.debug("looking for %s",var)
    a = False
    if var in key2pbs:
        logger.debug("looking for %s",key2pbs[var])
        a=where.get(key2pbs[var])
    if not a and var in key2slurm:
        logger.debug("looking for %s",key2slurm[var])
        a=where.get(key2slurm[var])
    if not a:
        logger.debug("%s not found",var)
        return False
    return a

def _check_and_create_metadata(raw_metadata):
# First check what should be here
    for n in [ 'job_pl_id', 'job_pl_submit_ts', 'job_pl_start_ts', 'job_pl_env', 
               'job_el_stop_ts', 'job_el_exitcode', 'job_el_reason', 'job_el_env' ]:
        s = str(raw_metadata.get(n))
        if not s:
            logger.error("Could not find %s in job metadata, job incomplete?",n)
            return False
        if len(s) == 0:
            logger.error("Null value of %s in job metadata, corrupt data?",n)
            return False
# Now look up any batch environment variables we may use
    username = get_batch_envvar("JOB_USER",raw_metadata['job_pl_env'])
    if username is False:
        username = getpwuid(getuid()).pw_name
        logger.warning("No job username found, defaulting to %s",username)
    jobname = get_batch_envvar("JOB_NAME",raw_metadata['job_pl_env'])
    if jobname is False:
        jobname = username+"-"+"interactive"
        logger.warning("No job name found, defaulting to %s",jobname)
# Look up job tags from stop environment
    job_tags = _get_tags_from_string(raw_metadata['job_el_env'].get(settings.job_tags_env))
    logger.info("job_tags: %s",str(job_tags))
# Compute difference in start vs stop environment
    env={}
    start_env=raw_metadata['job_pl_env']
    stop_env=raw_metadata['job_el_env']
    for e in start_env.keys():
        if e in stop_env.keys():
            if start_env[e] == stop_env[e]:
                logger.debug("Found "+e)
            else:
                logger.debug("Different "+e)
                env[e] = stop_env[e]
        else:
            logger.debug("Deleted "+e)
            env[e] = start_env[e]
    for e in stop_env.keys():
        if e not in start_env.keys():
            logger.debug("Added "+e)
            env[e] = stop_env[e]
    env_changes = env
# Augment the metadata
    metadata = raw_metadata
    metadata['job_username'] = username
    metadata['job_jobname'] = jobname
    metadata['job_env_changes'] = env_changes
    metadata['job_tags'] = job_tags

    return metadata

@db_session
def ETL_job_dict(raw_metadata, filedict, settings, tarfile=None):
# Synthesize what we need
    metadata = _check_and_create_metadata(raw_metadata)
    if metadata is False:
        return False

# Fields used in this function
    jobid = metadata['job_pl_id']
    username = metadata['job_username']
    start_ts = metadata['job_pl_start_ts']
    stop_ts = metadata['job_el_stop_ts']
    submit_ts = metadata['job_pl_submit_ts']
    jobname = metadata['job_jobname']
    exitcode = metadata['job_el_exitcode']
    reason = metadata['job_el_reason']
    env_dict = metadata['job_pl_env']
    env_changes_dict = metadata['job_env_changes']
    job_tags = metadata['job_tags']

#    info_dict = metadata['job_pl_from_batch'] # end batch also

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

    # not used anywhere
    # standards = [ "exename","path","args","pid","generation","ppid","pgid","sid","numtids","tid","start","end" ]

    # Initialize elements used in compute
    then = datetime.datetime.now()
    csvt = datetime.timedelta()
    earliest_process = datetime.datetime.utcnow()
    latest_process = datetime.datetime.fromtimestamp(0)

#    stdout.write('-')
# Hostname, job, metricname objects
# Iterate over hosts

    logger.debug("Iterating over %d hosts for job ID %s, user %s...",len(filedict.keys()),jobid,username)

#
# Create user and job object
#
    u = lookup_or_create_user(username)
    j = create_job(jobid,u)
    if not j: # FIX! We might have leaked a username to the database here
        return None
    j.jobname = jobname
    j.exitcode = exitcode
# fix below
    j.env_dict = env_dict
    j.env_changes_dict = env_changes_dict
#    j.info_dict = info_dict

    didsomething = False
    all_tags = set([])
    all_procs = []

    # a pid_map is used to create the process graph
    pid_map = {}  # maps pids to process objects

    for hostname, files in filedict.iteritems():
        logger.debug("Processing host %s",hostname)
        # we only need to a lookup_or_create_host if papiex doesn't
        # have a hostname column
        # h = lookup_or_create_host(hostname)
        cntmax = len(files)
        cnt = 0
        for f in files:
            # if cnt > 1000: break # for debugging
            logger.debug("Processing file %s",f)
#
#            stdout.write('\b')            # erase the last written char
#            stdout.write(spinner.next())  # write the next character
#            stdout.flush()                # flush stdout buffer (actual character display)
#
            csv = datetime.datetime.now()
# We need rows to skip
# oldproctag (after comment char) is outdated as a process tag but kept for posterities sake
            rows,oldproctag = extract_tags_from_comment_line(f,tarfile=tarfile)
            logger.debug("%s had %d comment rows, oldproctags %s",f,rows,oldproctag)
# Check comment/tags cache
#            if comment:
# Merge all tags into one list for job
#                all_tags.add(comment)

            if tarfile:
                info = tarfile.getmember(f)
                flo = tarfile.extractfile(info)
            else:
                flo = f
                
            from pandas import read_csv
            collated_df = read_csv(flo,
                                   sep=",",
                                   #dtype=dtype_dic, 
                                   converters=conv_dic,
                                   skiprows=rows, escapechar='\\')
            if collated_df.empty:
                logger.error("Something wrong with file %s, readcsv returned empty, skipping...",f)
                continue

# Make Process/Thread/Metrics objects in DB
            # there are 1 or more process dataframes in the collated df
            # let's iterate over them
            for df in _get_process_df(collated_df):
                # we provide the hostname argument as a fallback in case
                # the papiex data doesn't have a hostname column
                p = load_process_from_pandas(df, hostname, j, u, settings)
                if not p:
                    logger.error("Failed loading from pandas, file %s!",f);
                    continue
# If using old version of papiex, process tags are in the comment field
                if not p.tags and oldproctag:
                    p.tags = _get_tags_from_string(oldproctag)

                pid_map[p.pid] = p
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
                    # break

#
        if cnt:
            didsomething = True

#    stdout.write('\b')            # erase the last written char

    if filedict:
        if not didsomething:
            logger.warning("Something went wrong in parsing CSV files")
            return False
    else:
        logger.warning("Submitting job with no CSV data, tags %s",str(job_tags))

# Add sum of tags to job        
#    if all_tags:
#        logger.info("Adding %d tags to job",len(all_tags))
        # once the tags becomes a string of key/value pairs, then
        # just use _get_tags_from_string instead of _get_tags_for_list
#        j.tags = _get_tags_for_list(all_tags)
# Add all processes to job
    if all_procs:
        _create_process_tree(pid_map)
        logger.info("Adding %d processes to job",len(all_procs))
        j.processes.add(all_procs)
# Update start/end/duration of job
#       j.start = earliest_process
#        j.end = latest_process
#
#
#
    j.start = start_ts
    j.end = stop_ts
    j.submit = submit_ts # Wait time is start - submit and should probably be stored
    d = j.end - j.start
    j.duration = int(d.total_seconds()*1000000)
    if job_tags:
        j.tags = job_tags
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
    print "Imported successfully - job:",jobid,"processes:",len(j.processes),"rate:",len(j.processes)/float((now-then).total_seconds())
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
# We should remove below here
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

