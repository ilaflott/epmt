from __future__ import print_function
from sqlalchemy import *
#from sqlalchemy.event import listens_for
#from sqlalchemy.pool import Pool
from sqlalchemy.orm import backref, relationship, sessionmaker, scoped_session, mapperlib
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm.query import Query
import threading
from functools import wraps
from os import chdir, getcwd, path

from logging import getLogger
logger = getLogger(__name__) 
import epmt.epmt_settings as settings

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
    #print(f'(general.py: db_session())------------FUNCTION CALL')
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not hasattr(thr_data, 'session') or (thr_data.session is None):
            thr_data.session = Session()  # (this is now a scoped session)
        session = thr_data.session
        if hasattr(thr_data, 'nestlevel'):
            thr_data.nestlevel += 1
        else:
            thr_data.nestlevel = 1
        completed = False
        retval = None
        try:
            retval = func(*args, **kwargs) # No need to pass session explicitly
            completed = True
        except Exception as e:
            logger.debug(str(e),exc_info=True)
            logger.warning('Rolling back due to exception: {}'.format(e))
            #, exc_info=True)
            # import traceback, sys
            # print('-'*60)
            # traceback.print_exc(file=sys.stdout)
            # print('-'*60)
            try:
                print(f'(general.py: db_session()) session.rollback()')
                session.rollback()
            except:
                print(f'(general.py: db_session()) exception caught, pass')
                pass
            print(f'(general.py: db_session()) exception caught, raise')
            raise
        finally:
            thr_data.nestlevel -= 1
            if thr_data.nestlevel == 0: 
                if completed:
                    print(f'(general.py: db_session()) session.commit()')
                    session.commit()
                #Session.remove()  # NOTE: *remove* rather than *close* here
        #print(f'\n(general.py: db_session())------------RETURNING retval')
        return retval
    return wrapper

# This is a low-level function, which is meant for internal use only
def _connect_engine():
    global engine
    if engine is None:
        try:
            engine = engine_from_config(settings.db_params, prefix='')
            thr_data.engine = engine
        except Exception as e:
            logger.error("create_engine from db_params failed")
            logger.error("Exception(%s): %s",type(e).__name__,str(e).strip())
            return False
    return engine

def setup_db(settings,drop=False,create=True):
    global db_setup_complete
    global engine

    if db_setup_complete and not(drop):
        logger.info('skipping DB setup as it has already been initialized')
        return True
    logger.info("Creating engine with db_params: %s", settings.db_params)
    _connect_engine()

    ## print the compile options
    # with engine.connect() as con:
    #     rs = con.execute('PRAGMA compile_options')
    #     for row in rs: print row

    if drop:
        logger.warning("DROPPING ALL DATA AND TABLES!")
        if Session:
            Session.rollback()
            Session.flush()
            Session.close()
        Base.metadata.drop_all(engine)
        # for tbl in Base.metadata.sorted_tables:
        #     engine.execute(tbl.delete())
        # remove alembic version table
        engine.execute('DROP TABLE IF EXISTS processes_staging')
        engine.execute('DROP TABLE IF EXISTS alembic_version')

    # migrations won't work with in-memory databases
    from epmt.orm import orm_in_memory
    if orm_in_memory():
        generate_schema_from_models()
    else:
        check_and_apply_migrations()

    logger.debug('Configuring scoped session..')
    # hide useless warning when re-configuring a session
    # sqlalchemy/orm/scoping.py:107: SAWarning: At least one scoped session is already present.  configure() can not affect sessions that have already been created.  "At least one scoped session is already present. "
    from epmt.epmtlib import capture
    with capture() as (out,err):
         Session.configure(bind=engine, expire_on_commit=False, autoflush=True)
    db_setup_complete = True
    return True


# This function is only-used for in-memory databases where
# migrations won't work
def generate_schema_from_models():
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
            return False
    else:
        logger.info("Generating mapping from schema..")
        try:
            Base.metadata.create_all(engine)
        except Exception as e:
            #logger.error("Mapping to DB, did the schema change? Perhaps drop and create?")
            logger.error("Exception(%s): %s",type(e).__name__,str(e).strip())
            return False
    return True


# orm_get(Job, '6355501')
# or
# orm_get(User, name='John.Doe')
def orm_get(model, pk=None, **kwargs):
    return Session.query(model).get(pk) if (pk != None) else Session.query(model).filter_by(**kwargs).one_or_none()

# def orm_get_or_create(model, **kwargs):
#     o = Session.query(model).with_for_update(of=model).filter_by(**kwargs).one()
#     if not o:
#         o = model(**kwargs)
#         Session.add(o)
#         Session.commit()
#     return o
 

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
    Session.flush()
    return o

def orm_delete(o):
    Session.delete(o)

def orm_delete_jobs(jobs, use_orm = False):
    print(f'(orm/sqlalchemy/general.py: orm_delete_jobs())------------FUNCTION CALL')
    if not use_orm:
        stmts = []
        for j in jobs:
            jobid = j.jobid
            # is the job processed in staging? If so, we need to
            # make sure the process rows corresponding to the job
            # in the staging table are deleted as part of this transaction
            if not j.info_dict.get('procs_in_process_table', 1):
                (first_proc_id, last_proc_id) = j.info_dict['procs_staging_ids']
                stmts.append("DELETE FROM processes_staging WHERE id BETWEEN {} AND {};\n".format(first_proc_id, last_proc_id))
            stmts.append('DELETE FROM ancestor_descendant_associations WHERE EXISTS (SELECT ad.* from ancestor_descendant_associations ad INNER JOIN processes p ON (ad.ancestor = p.id OR ad.descendant = p.id) WHERE p.jobid = \'{0}\')'.format(jobid))
            stmts.append('DELETE FROM host_job_associations WHERE host_job_associations.jobid = \'{0}\''.format(jobid))
            stmts.append('DELETE FROM refmodel_job_associations WHERE refmodel_job_associations.jobid = \'{0}\''.format(jobid))
            stmts.append('DELETE FROM processes WHERE processes.jobid = \'{0}\''.format(jobid))
            stmts.append('DELETE FROM jobs WHERE jobs.jobid = \'{0}\''.format(jobid))
        try:
            orm_raw_sql(stmts, commit = True)
            print(f'\n(orm/sqlalchemy/general.py: orm_delete_jobs())------------RETURNING True')
            return True
        except Exception as e:
            #print(f'\n(orm/sqlalchemy/general.py: orm_delete_jobs())------------EXCEPTION THROWN!') # if the logger.debug line in orm_raw_sql throws an exception,
            #assert(False)                                                                           # this and the following assert statement are executed.
            # postgres permission denied for R/O accounts
            if 'permission denied' in str(e):
                logger.error('You do not have sufficient privileges to delete jobs')
                print(f'\n(orm/sqlalchemy/general.py: orm_delete_jobs())------------RETURNING False')
                return False
            logger.warning("Could not execute delete SQL: {0}".format(str(e)))

    # do a slow delete using ORM
    logger.warning("Fast-path delete did not work. Doing a slow delete using ORM..")
    for j in jobs:
        #print(f'(orm_delete_jobs) deleting job j={j}')
        Session.delete(j)
    Session.commit()

    print(f'\n(orm/sqlalchemy/general.py: orm_delete_jobs())------------RETURNING True')
    return True


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
    from epmt.epmtlib import isString
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
    print(f'(orm/sqlalchemy/general.py: orm_jobs_col())------------FUNCTION CALL')
    """
    This is an internal function that returns a Job Query object.
    The input can be collection of jobs spcified as a string, a list
    of strings, list of dicts, a dataframe or a list of Job objects.
    """
    from pandas import DataFrame
    from epmt.epmtlib import isString
    from .models import Job
    
    if orm_is_query(jobs):
        print(f'\n(orm/sqlalchemy/general.py: orm_jobs_col())------------RETURNING jobs')
        return jobs

    if ((type(jobs) != DataFrame) and not(jobs)):
        print(f'type(jobs)!=DataFrame, and jobs is empty.')
        print(f'\n(orm/sqlalchemy/general.py: orm_jobs_col())------------RETURNING Session.query(Job)')
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
        print(f'\n(orm/sqlalchemy/general.py: orm_jobs_col())------------RETURNING Session.query(Job).filter(Job.jobid == jobs.jobid)')
        return Session.query(Job).filter(Job.jobid == jobs.jobid)

    if type(jobs) in [list, set]:
        # jobs is a list of Job objects or a list of jobids or a list of dicts
        # so first convert the dict list to a jobid list
        jobs = [ j['jobid'] if type(j) == dict else j for j in jobs ]
        jobs = [ j.jobid if type(j)==Job else j for j in jobs ]
        # and now convert to a Query object so the user can chain
        jobs = Session.query(Job).filter(Job.jobid.in_(jobs))

    print(f'\n(orm/sqlalchemy/general.py: orm_jobs_col())------------RETURNING jobs')
    return jobs


def orm_to_dict(obj, **kwargs):
    from .models import Job, Process, User, Host, ReferenceModel
    from epmt.epmtlib import isString
    # we need to make sure jobs are post-processed first and foremost
    # This step has to be done before we get a dict from the object
    if type(obj) == Job:
        from epmt.epmt_query import is_job_post_processed
        if not(is_job_post_processed(obj.jobid)):
            from epmt.epmt_job import post_process_job
            trigger_pp = kwargs.get('trigger_post_process', True)
            if trigger_pp:
                post_process_job(obj.jobid) # as a side-effect obj.proc_sums will be populated

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


def orm_get_procs(jobs, tags, fltr, order, limit, offset, when, hosts, exact_tag_only, columns=None):
    from .models import Process, Host
    from epmt.epmtlib import tags_list, isString
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
    if offset:
        qs = qs.offset(offset)

    return qs

def orm_get_jobs(qs, tags, fltr, order, limit, offset, when, before, after, hosts, annotations, analyses, exact_tag_only, processed = None):
    print(f'(orm/sqlalchemy/general.py: orm_get_jobs())------------FUNCTION CALL')
    print(f'args: limit={limit}, before={before}, after ={after}')
    #print(f'args: qs=\n {qs} \n')
    
    from .models import Job, Host
    from epmt.epmtlib import tags_list, isString, tag_from_string
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

    if processed is not None:
        qs = _attribute_filter(qs, 'info_dict', {'post_processed': 1 if processed else 0}, model = Job, conv_to_str = True)

    if not(order is None):
        qs = qs.order_by(order)

    # finally set limits on the number of jobs returned
    if limit:
        print(f'(orm_get_jobs) setting limit to {limit}')
        qs = qs.limit(int(limit))

    if offset:
        qs = qs.offset(offset)
        
    print(f'\n(orm/sqlalchemy/general.py: orm_get_jobs())------------RETURNING qs')
    return qs


def _tag_filter(qs, tag, exact_match, model=None):
    return _attribute_filter(qs, 'tags', tag, exact_match, model)

# common low-level function to handle dict attribute filters
def _attribute_filter(qs, attr, target, exact_match = False, model = None, conv_to_str = True):
    from .models import Job
    using_sqlite = 'sqlite' in settings.db_params.get('url', '')
    using_postgres = 'postgres' in settings.db_params.get('url', '')
    if not (using_sqlite or using_postgres):
        raise NotImplementedError("sqlalchemy JSON attribute filtering only works for SQLite and Postgresql at present")
    if (model == None): model = Job
    if exact_match or (target == {}):
        qs = qs.filter(getattr(model, attr) == target)
    else:
        # we consider a match if the model attribute is a superset
        # of the passed tag
        for (k,v) in target.items():
            if conv_to_str or (type(v) == str):
                qs = qs.filter(text("cast(json_extract({0}.{1}, '$.{2}') as text) = '{3}'".format(model.__tablename__, attr, k, v)) if using_sqlite else (getattr(model, attr)[k].astext == str(v)))
            else:
                qs = qs.filter(text("json_extract({0}.{1}, '$.{2}') = {3}".format(model.__tablename__, attr, k, v)) if using_sqlite else (getattr(model, attr)[k] == v))
    return qs


def _annotation_filter(qs, annotations):
    from .models import Job
    return _attribute_filter(qs, 'annotations', annotations, model = Job, conv_to_str = True)

def _analyses_filter(qs, analyses):
    from .models import Job
    return _attribute_filter(qs, 'analyses', analyses, model = Job, conv_to_str = True)

def orm_get_refmodels(name = None, tag = {}, fltr=None, limit=0, order=None, before=None, after=None, exact_tag_only=False):
    from .models import ReferenceModel

    qs = Session.query(ReferenceModel).filter_by(name=name) if (name is not None) else Session.query(ReferenceModel)

    if tag:
        qs = _tag_filter(qs, tag, exact_tag_only, ReferenceModel)

    # if fltr is a lambda function or a string apply it
    if not (fltr is None):
        qs = qs.filter(fltr)

    if not (before is None):
        qs = qs.filter(ReferenceModel.created_at <= before)

    if not (after is None):
        qs = qs.filter(ReferenceModel.created_at >= after)

    if not (order is None):
        qs = qs.order_by(order)

    # finally set limits on the number of processes returned
    if limit:
        qs = qs.limit(int(limit))

    return qs

def orm_dump_schema(show_attributes=True):
    '''
    Prints the schema to stdout. If show_attributes is
    disabled then the list of tables is returned instead.
    '''
    if show_attributes:
        # we only use the metadata for in-memory databases. For all
        # persistent backends, the migration scripts are the source of truth.
        from orm import orm_in_memory
        if not orm_in_memory():
            return alembic_dump_schema()

        # alteratively return [t.name for t in Base.metadata.sorted_tables]
        for t in Base.metadata.sorted_tables: 
            print('\nTABLE', t.name)
            for c in t.columns:
                try:
                    print('%20s\t%10s' % (c.name, str(c.type)))
                except:
                    print('%20s\t%10s' % (c.name, str(c.type.__class__.__name__.split('.')[-1])))
    else:
        m = MetaData()
        m.reflect(engine) # Read what exists on db so we can have full picture
        return [table.name for table in m.tables.values()]

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
def orm_raw_sql(sql, commit = False):
    print(f'(general.py: orm_raw_sql(sql,commit))------------FUNCTION CALL')
    #print(f'args: sql={sql}')
    #print(f'args: commit={commit}')
    
    # As we may get really long queries when moving processes from staging,
    # only log the first 1k of long queries
    logger.debug('Executing: {0}'.format(  ("... SQL too long, first 1024 entries are ...\n".join(map(str,sql[:1024]))) if len(sql) > 1024 else sql  ))
    #assert(False)
    
    print(f'attempting to connect to engine')
    connection = engine.connect()
    print(f'attempting to begin transaction')
    trans = connection.begin()
    if type(sql) != list:
        sql = [sql]
    try:
        print(f'(general.py: orm_raw_sql(sql,commit)) trying to execute sql statements one-by-one')
        exe_count=0
        tot_exe_count=len(sql)
        for s in sql:
            if exe_count%100==0:
                print(f'executing statement #{exe_count} out of {tot_exe_count}')
            res = connection.execute(s)
            exe_count=exe_count+1
        if commit:
            trans.commit()
            return True
    except:
        print(f'(general.py: orm_raw_sql(sql,commit)) exception caught, rolling back trans=connection.begin()')
        trans.rollback()
        raise
    print(f'(general.py: orm_raw_sql(sql,commit)) closing connection')
    connection.close()
    print(f'(general.py: orm_raw_sql(sql,commit)) ------------RETURNING res')
    return res


def set_sql_debug(discard):
    print('setting/unsetting SQL debug is not supported on-the-fly')
    print('Try changing the value of the "echo" key in the settings.py:db_params')
    return False

# This decorator will change the directory to the directory
# containing alembic.ini (install dir) and then restore
# the working directory on end of function
def chdir_for_alembic_and_restore_cwd(function):
   def decorator(*args, **kwargs):
      cwd = getcwd()
      # change dir to install root
      # install_dir = path.dirname(path.abspath(__file__)) + "/../../"
      # The above path.dirname won't work with pyinstaller as the path is fake
      # So, derive install dir from papiex install prefix
      # Unfortunately we have two different paths, one for
      # development and one for production. So try the other
      # if the first fails.
      # TODO: We have to have a better way than this gross hack below!
      # try:
      #     chdir(settings.install_prefix + "/../../epmt")
      # except FileNotFoundError:
#     #      logger.warning(settings.install_prefix + "/../../epmt")
      #     try:
      #         chdir(settings.install_prefix + "/../epmt-install/epmt")
      #     except FileNotFoundError:
#     #          logger.warning(settings.install_prefix + "/../epmt-install/epmt")
      #         pass
      from epmt.epmtlib import get_install_root
      install_dir = get_install_root()
      try:
          chdir(install_dir)
      except:
          logger.error('Could not change directory to {} for migrations'.format(install_dir))
          raise
      result = function(*args, **kwargs)
      # restore directory to cwd
      chdir(cwd)
      return result
   return decorator

@chdir_for_alembic_and_restore_cwd
def check_and_apply_migrations():
    from alembic import config, script
    database_schema_version = get_db_schema_version()
    alembic_cfg = config.Config('epmt/alembic.ini')
    script_ = script.ScriptDirectory.from_config(alembic_cfg)
    epmt_schema_head = script_.get_current_head()

    if database_schema_version != epmt_schema_head:
        logger.debug('database schema version: {}'.format(database_schema_version))
        logger.debug('EPMT schema HEAD: {}'.format(epmt_schema_head))
        logger.info('Database needs to be upgraded..')
        return migrate_db()
    else:
        logger.info('database schema up-to-date (version {})'.format(epmt_schema_head))
    return True

@chdir_for_alembic_and_restore_cwd
def get_db_schema_version():
    from alembic import config
    from alembic.runtime import migration
    engine = _connect_engine()
    alembic_cfg = config.Config('epmt/alembic.ini')
    with engine.begin() as conn:
        context = migration.MigrationContext.configure(conn)
        database_schema_version = context.get_current_revision()
    return database_schema_version


@chdir_for_alembic_and_restore_cwd
def migrate_db():
    from alembic import config, script
    from sqlalchemy import exc
    alembic_cfg = config.Config('epmt/alembic.ini')
    script_ = script.ScriptDirectory.from_config(alembic_cfg)
    epmt_schema_head = script_.get_current_head()
    logger.info('Migrating database to HEAD: {}'.format(epmt_schema_head))
    try:
        config.main(argv=['--raiseerr', 'upgrade', 'head',])
    except Exception as e:
        logger.error('Could not upgrade the database')
        if 'permission denied' in str(e):
            logger.error('Looks like you do not have sufficient privileges to migrate the database')
        raise
    updated_version = get_db_schema_version()
    if updated_version != epmt_schema_head:
        logger.warning('Database migration failed. Current schema version is {}, while head is {}'.format(updated_version, epmt_schema_head))
    else:
        logger.info('Database successfully migrated to: {}'.format(epmt_schema_head))
    return (epmt_schema_head == updated_version)

@chdir_for_alembic_and_restore_cwd
def alembic_dump_schema(version = ''):
    '''
    This functions dumps the raw SQL needed to generate the
    schema upto the specified schema version. If the version
    is unspecified HEAD is assumed.
    '''
    from alembic import config
    if not version:
        version = get_db_schema_version()
    logger.info('Dumping schema upto version: {}'.format(version))
    try:
        config.main(argv=['upgrade', '--sql', version,])
    except:
        pass

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

