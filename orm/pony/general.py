# general.py
from pony.orm import *
from logging import getLogger
logger = getLogger(__name__)  # you can use other name
import init_logging

db = Database()

logger.info('Pony ORM selected')

### API ###
def setup_db(settings,drop=False,create=True):
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

@db_session
def get_(model, pk=None, **kwargs):
    if pk != None:
        try:
            return model[pk]
        except:
            return None
    return model.get(**kwargs)

@db_session
def create_(model, **kwargs):
    return model(**kwargs)
