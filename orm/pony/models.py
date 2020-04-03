from .general import *
from datetime import datetime

# Removing/changing hosts needs to be addressed
#
class Host(db.Entity):
    created_at = Required(datetime, default=datetime.utcnow)
    updated_at = Required(datetime, default=datetime.utcnow)
    info_dict = Optional(Json)
    # end template
    name = PrimaryKey(str)
    processes = Set('Process')
    jobs = Set('Job')
#
# A job is a separate but possibly connected entity to an experiment/postprocess run
#
class Job(db.Entity):
# Rollup entries, computed at insert time
    start = Required(datetime, default=datetime.utcnow)
    end = Required(datetime, default=datetime.utcnow)
    duration = Required(float, default=0)
    proc_sums = Optional(Json) # proc_sums contains aggregates across processes
# End rollups
    created_at = Required(datetime, default=datetime.utcnow)
    updated_at = Required(datetime, default=datetime.utcnow)
    info_dict = Optional(Json, default={})
    annotations = Optional(Json, default={})
    analyses = Optional(Json, default={})
# End generic template
    env_dict = Optional(Json)
    env_changes_dict = Optional(Json)
    submit = Optional(datetime)
    jobid = PrimaryKey(str)
    jobname = Optional(str)
    exitcode = Optional(int)
    user = Required('User')
    hosts = Set('Host')
    processes = Set('Process', cascade_delete=True)
    tags = Optional(Json)
#   ppr = Optional('PostProcessRun')
    # exclusive cpu time
    cpu_time = Optional(float)
    ref_models = Set('ReferenceModel')


class Process(db.Entity):
# Rollup entries, computed at insert time
    start = Required(datetime, default=datetime.utcnow)
    end = Required(datetime, default=datetime.utcnow)
    duration = Required(float, default=0)
# End rollup
    created_at = Required(datetime, default=datetime.utcnow)
    updated_at = Required(datetime, default=datetime.utcnow)
#   info_dict = Optional(Json)
# End generic template
    tags = Optional(Json)
    job = Required('Job')
    host = Required('Host')
    user = Required('User')
    threads_df = Optional(Json)
    threads_sums = Optional(Json)
    numtids = Required(int, default=1)
    # exclusive cpu time
    cpu_time = Optional(float)
# sum of cpu times of all descendants + process_cpu_time
    inclusive_cpu_time = Optional(float)
# These should probably be abstracted/reduced
    exename = Required(str)
    path = Required(str)
    args = Optional(str)
#   env_dict = Optional(Json)
# End above
    pid = Required(int)
    ppid = Required(int)
    pgid = Required(int)
    sid = Required(int)
    gen = Required(int)
    exitcode = Optional(int)
# for creating a process graph
# a child process is also included in the list of descendants
# while parent is included in the ancestors
    parent = Optional('Process', reverse="children")
    children = Set('Process', reverse="parent")
    ancestors = Set('Process', reverse="descendants")
    descendants = Set('Process', reverse="ancestors")
    depth = Optional(int) # depth in process tree; root process has depth 0

# class Thread(db.Entity):
# # These are measured
#   start = Required(datetime)
#   end = Required(datetime)
# # This is computed at insert time
#   duration = Required(float)
# # updated_at = Required(datetime, default=datetime.utcnow)
# # info_dict = Optional(Json)
# # End generic template
#   tid = Required(int)
#   metrics = Optional(Json)
#   process = Required(Process)
# # calipers = Set('Calipers')

#class Caliper(db.Entity):
#   name = Required(str)
#   metrics = Set('Metric')
#   duration = Required(datetime.timedelta)
#   parent = Required(Thread) # Fix: Could be process or host

# class MetricName(db.Entity):
#   name = PrimaryKey(str)
#   metrics = Set('Metric')

# class Metric(db.Entity):
#   metricname = Required('MetricName')
#   value = Required(float)
#   thread = Required(Thread)

class User(db.Entity):
    created_at = Required(datetime, default=datetime.utcnow)
    updated_at = Required(datetime, default=datetime.utcnow)
    info_dict = Optional(Json)
    # end template
    name = PrimaryKey(str)
    id = Optional(int,unique=True)
#   exps = Set('Experiment')
#   pprs = Set('PostProcessRun')
    jobs = Set('Job')
    processes = Set('Process', cascade_delete=True)

# class Group(db.Entity):
#     created_at = Required(datetime, default=datetime.utcnow)
#     updated_at = Required(datetime, default=datetime.utcnow)
#     info_dict = Optional(Json)
#     # end template
#     name = PrimaryKey(str)
#     id = Required(int,unique=True)
#     jobs = Set('Job')
#     processes = Set('Process')
#     users = Set('User')

# class Queue(db.Entity):
#     created_at = Required(datetime, default=datetime.utcnow)
#     updated_at = Required(datetime, default=datetime.utcnow)
#     info_dict = Optional(Json)
#     # end template
#     name = PrimaryKey(str)
#     id = Optional(int,unique=True)
#     jobs = Set('Job')   
# 
# class Account(db.Entity):
#     created_at = Required(datetime, default=datetime.utcnow)
#     updated_at = Required(datetime, default=datetime.utcnow)
#     info_dict = Optional(Json)
#     # end template
#     name = PrimaryKey(str)
#     id = Optional(int,unique=True)
#     jobs = Set('Job')

class ReferenceModel(db.Entity):
    created_at = Required(datetime, default=datetime.utcnow)
    updated_at = Required(datetime, default=datetime.utcnow)
    info_dict = Optional(Json)
    tags = Optional(Json)
    op_tags = Optional(Json)
    computed = Optional(Json)
    enabled = Required(bool, default=True)
    jobs = Set('Job')
    name = Optional(str,unique=True)

class UnprocessedJob(db.Entity):
    pass

