# general.py
from pony.orm.core import Query, QueryResult
from pony.orm.ormtypes import TrackedDict
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

def get_(model, pk=None, **kwargs):
    if pk != None:
        try:
            return model[pk]
        except:
            return None
    return model.get(**kwargs)

def create_(model, **kwargs):
    return model(**kwargs)

def commit_():
    return commit()

def add_to_collection_(collection, item):
    return collection.add(item)

def sum_attribute_(collection, attribute):
    return sum(getattr(collection, attribute))

def is_query(obj):
    return type(obj) in (Query, QueryResult)

def jobs_col(jobs):
    """
    This is an internal function to take a collection of jobs
    in a variety of formats and return output in the ORM format.
    """
    if is_query(jobs):
        return jobs
    from pd import DataFrame
    if ((type(jobs) != DataFrame) and not(jobs)):
        return Job.select()
    if type(jobs) == DataFrame:
        jobs = list(jobs['jobid'])
    if isString(jobs):
        if ',' in jobs:
            # jobs a string of comma-separated job ids
            jobs = [ j.strip() for j in jobs.split(",") ]
        else:
            # job is a single jobid
            jobs = Job[jobs]
    if type(jobs) == Job:
        # is it a singular job?
        jobs = [jobs]
    if type(jobs) in [list, set]:
        # jobs is a list of Job objects or a list of jobids or a list of dicts
        # so first convert the dict list to a jobid list
        jobs = [ j['jobid'] if type(j) == dict else j for j in jobs ]
        jobs = [ Job[j] if isString(j) else j for j in jobs ]
        # and now convert to a pony Query object so the user can chain
        jobs = Job.select(lambda j: j in jobs)
    return jobs

def to_dict(obj):
    return obj.to_dict()
