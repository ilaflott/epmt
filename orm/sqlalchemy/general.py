# general.py
from sqlalchemy import *
from sqlalchemy.orm import backref, relationship, sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
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
    logger.info("Creating engine with db_params: %s", settings.db_params)
    try:
        engine = engine_from_config(settings.db_params, prefix='')
    except Exception as e:
        logger.error("create_engine from db_params failed")
        logger.error("Exception(%s): %s",type(e).__name__,str(e).strip())
        return False

    if drop:
        logger.warning("DROPPING ALL DATA AND TABLES!")
        Base.metadata.drop_all(engine)

    logger.info("Generating mapping from schema...")
    try:
        Base.metadata.create_all(engine)
    except Exception as e:
        logger.error("Mapping to DB, did the schema change? Perhaps drop and create?")
        logger.error("Exception(%s): %s",type(e).__name__,str(e).strip())
        return False
    logger.info('Creating scoped session..')
    #Session.configure(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    global Session
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

### end API ###

# def get_session():
#     if hasattr(get_session, 'session'): return get_session.session
#     get_session.session = Session()
#     return get_session.session


