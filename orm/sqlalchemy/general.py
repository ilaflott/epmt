# general.py
from sqlalchemy import *
from sqlalchemy.orm import backref, relationship
from sqlalchemy.ext.declarative import declarative_base

from logging import getLogger
logger = getLogger(__name__)  # you can use other name
import init_logging

logger.info('sqlalchemy orm selected')
Base = declarative_base()

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

    if drop:
        logger.warning("Not implemented for sqlalchemy")
    return True

