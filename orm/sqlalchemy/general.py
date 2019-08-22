# general.py
from sqlalchemy import *
from sqlalchemy.orm import backref, relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from logging import getLogger
logger = getLogger(__name__)  # you can use other name
import init_logging

logger.info('sqlalchemy orm selected')
Base = declarative_base()
Session = sessionmaker()

### sqlalchemy-specific API implementation ###

def setup_db(settings,drop=False,create=True):
    logger.info("Creating engine with db_params: %s", settings.db_params)
    try:
        engine = engine_from_config(settings.db_params, prefix='')
    except Exception as e:
        logger.error("create_engine from db_params failed")
        logger.error("Exception(%s): %s",type(e).__name__,str(e).strip())
        return False

    logger.info("Generating mapping from schema...")
    try:
        Base.metadata.create_all(engine)
    except Exception as e:
        logger.error("Mapping to DB, did the schema change? Perhaps drop and create?")
        logger.error("Exception(%s): %s",type(e).__name__,str(e).strip())
        return False
    logger.info('Creating session..')
    Session.configure(bind=engine)
    if drop:
        logger.warning("Not implemented for sqlalchemy")
    return True

# get_(Job, '6355501')
# or
# get_(User, name='John.Doe')
def get_(model, pk=None, **kwargs):
    return get_session().query(model).get(pk) if (pk != None) else get_session().query(model).filter_by(**kwargs).one_or_none()

def create_(model, autocommit=True, **kwargs):
    o = model(**kwargs)
    s = get_session()
    s.add(o)
    if autocommit:
        s.commit()
    return o

def commit_():
    get_session().commit()

### end API ###

def get_session():
    if hasattr(get_session, 'session'): return get_session.session
    get_session.session = Session()
    return get_session.session
