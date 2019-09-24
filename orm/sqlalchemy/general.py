from __future__ import print_function
from sqlalchemy import *
#from sqlalchemy.event import listens_for
#from sqlalchemy.pool import Pool
from sqlalchemy.orm import backref, relationship, sessionmaker, scoped_session, mapperlib
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
thr_data.session = None
Session = scoped_session(sessionmaker())
engine = None
db_setup_complete = False

### sqlalchemy-specific API implementation ###
def db_session(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if thr_data.session is None:
            thr_data.session = Session()  # (this is now a scoped session)
        session = thr_data.session
        thr_data.nestlevel += 1
        completed = False
        try:
            retval = func(*args, **kwargs) # No need to pass session explicitly
            completed = True
        except Exception as e:
            import traceback, sys
            logger.error('\nAn exception occurred: {0}\nWill rollback session..'.format(e))
            print('-'*60)
            traceback.print_exc(file=sys.stdout)
            print('-'*60)
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
    global db_setup_complete
    global engine

    if db_setup_complete:
        logger.debug('skipping DB setup as it has already been initialized')
        return True
    logger.info("Creating engine with db_params: %s", settings.db_params)
    if engine is None:
        try:
            engine = engine_from_config(settings.db_params, prefix='')
            thr_data.engine = engine
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
        #if Session:
        #    Session.rollback()
        #    Session.expire_all()
        #    Session.remove()
        #    Session = None
        Base.metadata.drop_all(engine)
        #meta = MetaData()
        #import contextlib
        #with contextlib.closing(engine.connect()) as con:
        #    trans = con.begin()
        #    for table in reversed(meta.sorted_tables):
        #        con.execute(table.delete())
        #    trans.commit()
    ins = inspect(engine)
    if len(ins.get_table_names()) >= 8:
        logger.info("Reflecting existing schema..")
        try:
            Base.metadata.reflect(bind=engine)
            #meta = MetaData()
            #meta.reflect(engine)
            # we can then produce a set of mappings from this MetaData
            #Base = automap_base(metadata=meta)
            #thr_data.Base = Base
            # calling prepare() just sets up mapped classes and relationships.
            #Base.prepare()
            #User, Process, Job = Base.classes.users, Base.classes.processes, Base.classes.jobs
        except:
            pass
    else:
        logger.info("Generating mapping from schema..")
        try:
            Base.metadata.create_all(engine)
        except Exception as e:
            #logger.error("Mapping to DB, did the schema change? Perhaps drop and create?")
            logger.error("Exception(%s): %s",type(e).__name__,str(e).strip())
            return False

    logger.info('Configuring scoped session..')
    Session.configure(bind=engine, expire_on_commit=False, autoflush=True)
    db_setup_complete = True
    return True

# orm_get(Job, '6355501')
# or
# orm_get(User, name='John.Doe')
def orm_get(model, pk=None, **kwargs):
    return Session.query(model).get(pk) if (pk != None) else Session.query(model).filter_by(**kwargs).one_or_none()


def orm_findall(model, **kwargs):
    return Session.query(model).filter_by(**kwargs)

# def orm_set(o, **kwargs):
#     for k in kwargs.keys():
#         setattr(o, k, kwargs[k])
#     #print('type Session', type(Session))
#     #print('type object', type(o))
#     #Session.add(o)
#     return o

def orm_create(model, **kwargs):
    o = model(**kwargs)
    Session.add(o)
    return o

def orm_delete(o):
    Session.delete(o)

def orm_delete_jobs(jobs, use_orm = False):
    if not use_orm:
        stmts = []
        for j in jobs:
            jobid = j.jobid
            stmts.append('DELETE FROM ancestor_descendant_associations WHERE EXISTS (SELECT ad.* from ancestor_descendant_associations ad INNER JOIN processes p ON (ad.ancestor = p.id OR ad.descendant = p.id) WHERE p.jobid = "{0}")'.format(jobid))
            stmts.append('DELETE FROM host_job_associations WHERE host_job_associations.jobid = "{0}"'.format(jobid))
            stmts.append('DELETE FROM refmodel_job_associations WHERE refmodel_job_associations.jobid = "{0}"'.format(jobid))
            stmts.append('DELETE FROM processes WHERE processes.jobid = "{0}"'.format(jobid))
            stmts.append('DELETE FROM jobs WHERE jobs.jobid = "{0}"'.format(jobid))
        try:
            _execute_raw_sql(stmts, commit = True)
            return
        except Exception as e:
            logger.warning("Could not execute delete SQL: {0}".format(str(e)))

    # do a slow delete using ORM
    logger.info("Doing a slow delete using ORM..")
    for j in jobs:
        Session.delete(j)
    Session.commit()
    return

def orm_delete_refmodels(ref_ids):
    from .models import ReferenceModel
    ref_models = Session.query(ReferenceModel).filter(ReferenceModel.id.in_(ref_ids))
    n = ref_models.count()
    if n < len(ref_ids):
        logger.warning("Request for deleting {0} model(s), but only found {1} models from your selection to delete".format(len(ref_ids), n))
    if n > 0:
        try:
            for r in ref_models:
                Session.delete(r)
            Session.commit()
        except Exception as e:
            logger.error(str(e))
            return 0
    return n


def orm_commit():
    return Session.commit()

def orm_add_to_collection(collection, item):
    if type(item) == list:
        for o in item:
            collection.append(o)
        return collection
    else:
        return collection.append(item)

def orm_sum_attribute(collection, attribute):
    return sum([getattr(c, attribute) for c in collection])

def orm_is_query(obj):
    return (type(obj) == Query)

def orm_procs_col(procs):
    """
    This is an internal function to take a collection of
    procs in a variety of formats and return output in the
    ORM format
    """
    from pandas import DataFrame
    from .models import Process
    from epmtlib import isString
    if orm_is_query(procs):
        return procs
    if ((type(procs) != DataFrame) and not(procs)):
        # empty list => select all processes
        return Session.query(Process)
    if type(procs) == DataFrame:
        procs = [int(pk) for pk in list(procs['id'])]
    if isString(procs):
        if ',' in procs:
            # procs a string of comma-separated ids
            procs = [ int(p.strip()) for p in procs.split(",") ]
        else:
            # procs is a single id, but specified as a string
            procs = [int(procs)]
    if type(procs) == int:
        # a single primary key
        procs = [procs]

    if type(procs) == Process:
        # is it a singular Process?
        procs = [procs.id]

    if type(procs) in [list, set]:
        # procs is a list of Process objects or a list of primary keys or a list of dicts
        # so first convert the dict list to a bid list
        procs = [ p['id'] if type(p) == dict else p for p in procs ]
        procs = [ p.id if type(p)==Process else p for p in procs ]
        # and now convert to a pony Query object so the user can chain
        procs = Session.query(Process).filter(Process.id.in_(procs))
    return procs


def orm_jobs_col(jobs):
    """
    This is an internal function that returns a Job Query object.
    The input can be collection of jobs spcified as a string, a list
    of strings, list of dicts, a dataframe or a list of Job objects.
    """
    from pandas import DataFrame
    from epmtlib import isString
    from .models import Job
    if orm_is_query(jobs):
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


def orm_to_dict(obj, **kwargs):
    from .models import Job, Process, User, Host, ReferenceModel
    from epmtlib import isString
    d = obj.__dict__.copy()
    excludes = kwargs['exclude'] if 'exclude' in kwargs else []
    if isString(excludes):
        excludes = [excludes]
    for k in excludes:
        if k in d:
            del d[k]
    if '_sa_instance_state' in d:
        del d['_sa_instance_state']
    if type(obj) == ReferenceModel:
        if kwargs.get('with_collections'):
            d['jobs'] = [j.jobid if type(j) == Job else j for j in obj.jobs ]
        else:
            del d['jobs']
    if type(obj) == Job:
        if 'processes' in d:
            del d['processes']
    if type(obj) == Process:
        d['job'] = obj.jobid
        d['jobid'] = obj.jobid
        del d['parent_id']
        if 'host_id' in d:
            d['host'] = d['host_id']
            del d['host_id']
        d['parent'] = obj.parent.id if obj.parent else None
    if 'hosts' in d:
        if kwargs.get('with_collections'):
            d['hosts'] = [h.name if type(h) == Host else h for h in obj.hosts]
        else:
            del d['hosts']
    if 'user_id' in d:
        #d['user'] = Session.query(User).get(d['user_id']).name
        d['user'] = d['user_id']
        del d['user_id']
    return d


def orm_get_procs(jobs, tags, fltr, order, limit, when, hosts, exact_tag_only, columns=None):
    from .models import Process, Host
    from epmtlib import tags_list, isString
    from datetime import datetime
    if columns is None:
        columns = [Process]
    if jobs:
        jobs = orm_jobs_col(jobs)
        jobs = [j.jobid for j in jobs]
        qs = Session.query(*columns).filter(Process.jobid.in_(jobs))
    else:
        # no jobs set, so expand the scope to all Process objects
        qs = Session.query(*columns)

    if not (fltr is None):
        if isString(fltr):
            # sql query, so use the text function
            qs = qs.filter(text(fltr))
        else:
            qs = qs.filter(fltr)

    # filter using tag if set
    # Remember, tag = {} demands an exact match with an empty dict!
    if tags != None:
        tags = tags_list(tags)
        idx = 0
        org_qs = qs
        for t in tags:
            # _tag_filter reqturs a query object corresponding to
            # the jobs that match a particular tag. We, then, do
            # do a UNION (OR operation) across these query sets.
            qst = _tag_filter(org_qs, t, exact_tag_only, Process)
            qs = qst if (idx == 0) else qs.union(qst)
            idx += 1


    if when:
        if type(when) == datetime:
            qs = qs.filter(Process.start <= when, Process.end >= when)
        else:
            when_process = orm_get(Process, when) if isString(when) else when
            qs = qs.filter(Process.start <= when_process.end, Process.end >= when_process.start)

    if hosts:
        qs = qs.join(Host, Process.host).filter(Host.name.in_(hosts))

    if not(order is None):
        qs = qs.order_by(order)

    # finally set limits on the number of jobs returned
    if limit:
        qs = qs.limit(int(limit))

    return qs

def orm_get_jobs(qs, tags, fltr, order, limit, offset, when, before, after, hosts, annotations, analyses, exact_tag_only):
    from .models import Job, Host
    from epmtlib import tags_list, isString, tag_from_string
    from datetime import datetime

    if not fltr is None:
        if isString(fltr):
            # sql query, so use the text function
            qs = qs.filter(text(fltr))
        else:
            qs = qs.filter(fltr)

    # filter using tags if set
    # Remember, tags = {} demands an exact match with an empty dict!
    if tags != None:
        tags = tags_list(tags)
        idx = 0
        org_qs = qs
        for t in tags:
            # _tag_filter reqturs a query object corresponding to
            # the jobs that match a particular tag. We, then, do
            # do a UNION (OR operation) across these query sets.
            qst = _tag_filter(org_qs, t, exact_tag_only)
            qs = qst if (idx == 0) else qs.union(qst)
            idx += 1

    # Remember, annotations = {} demands an exact match with an empty dict!
    if annotations != None:
        if type(annotations) == str:
            annotations = tag_from_string(annotations)
        qs = _annotation_filter(qs, annotations)

    # Remember, annotations = {} demands an exact match with an empty dict!
    if analyses != None:
        if type(analyses) == str:
            analyses = tag_from_string(analyses)
        qs = _analyses_filter(qs, analyses)

    if when:
        if type(when) == datetime:
            qs = qs.filter(Job.start <= when, Job.end >= when)
        else:
            when_job = orm_get(Job, when) if isString(when) else when
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


def _tag_filter(qs, tag, exact_match, model=None):
    return _attribute_filter(qs, 'tags', tag, exact_match, model)

# common low-level function to handle dict attribute filters
def _attribute_filter(qs, attr, target, exact_match = False, model = None, conv_to_str = True):
    from .models import Job
    if (model == None): model = Job
    if exact_match or (target == {}):
        qs = qs.filter(getattr(model, attr) == target)
    else:
        # we consider a match if the model attribute is a superset
        # of the passed tag
        for (k,v) in target.items():
            if conv_to_str or (type(v) == str):
                qs = qs.filter(text("json_extract({0}.{1}, '$.{2}') = '{3}'".format(model.__tablename__, attr, k, v)))
            else:
                qs = qs.filter(text("json_extract({0}.{1}, '$.{2}') = {3}".format(model.__tablename__, attr, k, v)))
    return qs


def _annotation_filter(qs, annotations):
    from .models import Job
    return _attribute_filter(qs, 'annotations', annotations, model = Job, conv_to_str = False)

def _analyses_filter(qs, analyses):
    from .models import Job
    return _attribute_filter(qs, 'analyses', analyses, model = Job, conv_to_str = False)

def orm_get_refmodels(tag = {}, fltr=None, limit=0, order=None, exact_tag_only=False):
    from .models import ReferenceModel

    qs = Session.query(ReferenceModel)

    qs = _tag_filter(qs, tag, exact_tag_only, ReferenceModel)

    # if fltr is a lambda function or a string apply it
    if not (fltr is None):
        qs = qs.filter(fltr)

    if not (order is None):
        qs = qs.order_by(order)

    # finally set limits on the number of processes returned
    if limit:
        qs = qs.limit(int(limit))

    return qs

def orm_dump_schema():
    for t in Base.metadata.sorted_tables: 
        print('\nTable', t.name)
        for c in t.columns:
            try:
                print('%20s\t%10s' % (c.name, str(c.type)))
            except:
                print('%20s\t%10s' % (c.name, str(c.type.__class__.__name__.split('.')[-1])))


### end API ###


# utility function to get Mapper from table
def get_mapper(tbl):
    mappers = [
        mapper for mapper in mapperlib._mapper_registry
        if tbl in mapper.tables
    ]
    if len(mappers) > 1:
        raise ValueError(
            "Multiple mappers found for table '%s'." % tbl.name
        )
    elif not mappers:
        raise ValueError(
            "Could not get mapper for table '%s'." % tbl.name
        )
    else:
        return mappers[0]


# This function is vulnerable to injection attacks. It's expected that
# the orm API will define a higher-level function to use this
# function after guarding against injection and dangerous sql commands
def _execute_raw_sql(sql, commit = False):
    connection = engine.connect()
    logger.debug('Executing: {0}'.format(sql))
    trans = connection.begin()
    if type(sql) != list:
        sql = [sql]
    try:
        for s in sql:
            res = connection.execute(s)
        if commit:
            trans.commit()
            return True
    except:
        trans.rollback()
        raise
    return res

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

