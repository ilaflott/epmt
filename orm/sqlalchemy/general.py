# general.py
from sqlalchemy import *
#from sqlalchemy.event import listens_for
#from sqlalchemy.pool import Pool
from sqlalchemy.orm import backref, relationship, sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.query import Query
import threading
from functools import wraps

from logging import getLogger
logger = getLogger(__name__)  # you can use other name
import init_logging

logger.info('sqlalchemy orm selected')
Base = declarative_base()

# we use this to keep track of db_session nesting since we only
# want to commit and remove the session when the top of the stack is popped
thr_data = threading.local()
thr_data.nestlevel = 0
Session = None

### sqlalchemy-specific API implementation ###
def db_session(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        session = Session()  # (this is now a scoped session)
        thr_data.session = session
        thr_data.nestlevel += 1
        completed = False
        try:
            retval = func(*args, **kwargs) # No need to pass session explicitly
            completed = True
        except:
            session.rollback()
            raise
        finally:
            thr_data.nestlevel -= 1
            if thr_data.nestlevel == 0: 
                if completed:
                    session.commit()
                #Session.remove()  # NOTE: *remove* rather than *close* here
        return retval
    return wrapper

def setup_db(settings,drop=False,create=True):
    global Session
    if Session:
        logger.debug('skipping DB setup as it has already been initialized')
        return True
    logger.info("Creating engine with db_params: %s", settings.db_params)
    try:
        engine = engine_from_config(settings.db_params, prefix='')
    except Exception as e:
        logger.error("create_engine from db_params failed")
        logger.error("Exception(%s): %s",type(e).__name__,str(e).strip())
        return False

    ## print the compile options
    # with engine.connect() as con:
    #     rs = con.execute('PRAGMA compile_options')
    #     for row in rs: print row

    if drop:
        logger.warning("DROPPING ALL DATA AND TABLES!")
        Base.metadata.drop_all(engine)

    logger.info("Generating mapping from schema...")
    try:
        Base.metadata.create_all(engine)
    except Exception as e:
        #logger.error("Mapping to DB, did the schema change? Perhaps drop and create?")
        logger.error("Exception(%s): %s",type(e).__name__,str(e).strip())
        return False
    logger.info('Creating scoped session..')
    #Session.configure(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    Session = scoped_session(session_factory)
    thr_data.Session = Session
    return True

# get_(Job, '6355501')
# or
# get_(User, name='John.Doe')
def get_(model, pk=None, **kwargs):
    return Session.query(model).get(pk) if (pk != None) else Session.query(model).filter_by(**kwargs).one_or_none()

def create_(model, **kwargs):
    o = model(**kwargs)
    Session.add(o)
    return o

def commit_():
    return Session.commit()

def add_to_collection_(collection, item):
    if type(item) == list:
        for o in item:
            collection.append(o)
        return collection
    else:
        return collection.append(item)

def sum_attribute_(collection, attribute):
    return sum([getattr(c, attribute) for c in collection])

def is_query(obj):
    return (type(obj) == Query)

def jobs_col(jobs):
    """
    This is an internal function that returns a Job Query object.
    The input can be collection of jobs spcified as a string, a list
    of strings, list of dicts, a dataframe or a list of Job objects.
    """
    from pandas import DataFrame
    from epmtlib import isString
    from .models import Job
    if is_query(jobs):
        return jobs
    if ((type(jobs) != DataFrame) and not(jobs)):
        return Session.query(Job)
    if type(jobs) == DataFrame:
        jobs = list(jobs['jobid'])
    if isString(jobs):
        if ',' in jobs:
            # jobs a string of comma-separated job ids
            jobs = [ j.strip() for j in jobs.split(",") ]
        else:
            # job is a single jobid
            jobs = Session.query(Job).filter_by(jobid=jobs)
    if type(jobs) == Job:
        # is it a singular job?
        return Session.query(Job).filter(Job.jobid == jobs.jobid)
    if type(jobs) in [list, set]:
        # jobs is a list of Job objects or a list of jobids or a list of dicts
        # so first convert the dict list to a jobid list
        jobs = [ j['jobid'] if type(j) == dict else j for j in jobs ]
        jobs = [ j.jobid if type(j)==Job else j for j in jobs ]
        # and now convert to a Query object so the user can chain
        jobs = Session.query(Job).filter(Job.jobid.in_(jobs))
    return jobs


def to_dict(obj):
    from .models import Job, User
    d = obj.__dict__
    if type(obj) == Job:
        if 'processes' in d:
            del d['processes']
        d['hosts'] = [h.name for h in obj.hosts]
        d['user'] = Session.query(User).get(d['user_id']).name
    return d

def orm_get_jobs_(qs, tags, order, limit, offset, when, before, after, hosts, exact_tag_only):
    from .models import Job, Host
    from epmtlib import tags_list

    # filter using tag if set
    # Remember, tag = {} demands an exact match with an empty dict!
    if tags != None:
        tags = tags_list(tags)
        qs_tags = []
        idx = 0
        org_qs = qs
        for t in tags:
            # tag_filter_ reqturs a query object corresponding to
            # the jobs that match a particular tag. We, then, do
            # do a UNION (OR operation) across these query sets.
            qst = tag_filter_(org_qs, t, exact_tag_only)
            qs = qst if (idx == 0) else qs.union(qst)
            idx += 1

    if when:
        if type(when) == datetime:
            qs = qs.filter(Job.start <= when, Job.end >= when)
        else:
            when_job = get_(Job, when) if isString(when) else when
            qs = qs.filter(Job.start <= when_job.end, Job.end >= when_job.start)

    if before != None:
        qs = qs.filter(Job.end <= before)

    if after != None:
        qs = qs.filter(Job.start >= after)
                

    if hosts:
        qs = qs.join(Host, Job.hosts).filter(Host.name.in_(hosts))

    if not(order is None):
        qs = qs.order_by(order)

    # finally set limits on the number of jobs returned
    if limit:
        qs = qs.limit(int(limit))
    if offset:
        qs = qs.offset(offset)

    return qs


def tag_filter_(qs, tag, exact_match, model=None):
    from .models import Job, Process
    if (model == None): model = Job
    if exact_match or (tag == {}):
        qs = qs.filter(model.tags == tag)
    else:
        # we consider a match if the job tag is a superset
        # of the passed tag
        for (k,v) in tag.items():
            #qs = qs.filter(model.tags[k] == cast(v, JSON))
            #qs = qs.filter(cast(model.tags[k], String) == type_coerce(v, JSON))
            #qs = qs.filter(model.tags[k] == str(v))
            qs = qs.filter(text("json_extract({0}.tags, '$.{1}') = '{2}'".format(model.__tablename__, k, v)))
    return qs



### end API ###

# def get_session():
#     if hasattr(get_session, 'session'): return get_session.session
#     get_session.session = Session()
#     return get_session.session

#@listens_for(Pool, "connect")
#def connect(dbapi_connection, connection_rec):
#    #print(dbapi_connection)
#    #print(connection_rec)
#    cursor = dbapi_connection.cursor()
#    result = cursor.execute("PRAGMA compile_options;")
#    cursor.close()
#    print("result=", result)
#    dbapi_connection.execute("PRAGMA compile_options;")
#    logger.info("loading json1 extension")
#     dbapi_connection.enable_load_extension(True)
#     dbapi_connection.load_extension("./json1.so")
#     dbapi_connection.enable_load_extension(False)
#     #dbapi_connection.do_sqlite_things()

