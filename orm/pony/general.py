# general.py
from pony.orm.core import Query, QueryResult
from pony.orm.ormtypes import TrackedDict
from pony.orm import *

from logging import getLogger
logger = getLogger('orm.pony')  # you can use other name

db = Database()

logger.info('Pony ORM selected')

### API ###
def setup_db(settings,drop=False,create=True):
    db_params = dict.copy(settings.db_params)
    if 'url' in db_params:
        db_params = _url2params(settings.db_params['url'])
        logger.debug('mapping db url to Pony-specific db params: %s', db_params)

    # FIX: There should be a better way than the hack below!
    # For relative filenames when using sqlite, we want to save
    # in the top-level directory and not in 'orm/pony' where this
    # module is, so we use an absolute path
    if ('filename' in db_params)  \
        and db_params['filename'] != ':memory:' \
        and (not (db_params['filename'].startswith('/'))):
        from os import getcwd
        db_params['filename'] = '{0}/{1}'.format(getcwd(), db_params['filename'])

    logger.info("Binding to DB: %s", db_params)

    try:
        db.bind(**db_params)
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

def orm_get(model, pk=None, **kwargs):
    if pk != None:
        try:
            return model[pk]
        except:
            return None
    return model.get(**kwargs)

def orm_findall(model, **kwargs):
    return model.select().filter(**kwargs)

# def orm_set(o, **kwargs):
#     o.set(**kwargs)
#     return o

def orm_create(model, **kwargs):
    return model(**kwargs)

def orm_delete(o):
    o.delete()

def orm_delete_jobs(jobs):
    for j in jobs:
        for p in j.processes:
            p.parent = None
    for j in jobs:
        for p in j.processes:
            p.delete()
    jobs.delete()

def orm_delete_refmodels(ref_ids):
    from .models import ReferenceModel

    ref_models = ReferenceModel.select(lambda r: r.id in ref_ids)
    n = ref_models.count()
    if n < len(ref_ids):
        logger.warning("Request for deleting {0} model(s), but only found {1} models from your selection to delete".format(len(ref_ids), n))
    if n > 0:
        try:
            for r in ref_models:
                for j in r.jobs:
                    j.ref_models.clear()
            ref_models.delete()
            commit()
        except Exception as e:
            logger.error(str(e))
            return 0
    return n



def orm_commit():
    return commit()

def orm_add_to_collection(collection, item):
    return collection.add(item)

def orm_sum_attribute(collection, attribute):
    return sum(getattr(collection, attribute))

def orm_is_query(obj):
    return type(obj) in (Query, QueryResult)

def orm_procs_col(procs):
    """
    This is an internal function to take a collection of
    procs in a variety of formats and return output in the
    ORM format
    """
    from pandas import DataFrame
    from .models import Process
    from epmtlib import isString
    if type(procs) in [Query, QueryResult]:
        return procs
    if ((type(procs) != DataFrame) and not(procs)):
        # empty list => select all processes
        return Process.select()
    if type(procs) == DataFrame:
        procs = [int(pk) for pk in list(procs['id'])]
    if isString(procs):
        if ',' in procs:
            # procs a string of comma-separated ids
            procs = [ int(p.strip()) for p in procs.split(",") ]
        else:
            # procs is a single id, but specified as a string
            procs = Process[int(procs)]
    if type(procs) == int:
        # a single primary key
        procs = Process[procs]

    if type(procs) == Process:
        # is it a singular Process?
        procs = [procs]

    if type(procs) in [list, set]:
        # procs is a list of Process objects or a list of primary keys or a list of dicts
        # so first convert the dict list to a bid list
        procs = [ p['id'] if type(p) == dict else p for p in procs ]
        procs = [ Process[p] if type(p)==int else p for p in procs ]
        # and now convert to a pony Query object so the user can chain
        procs = Process.select(lambda p: p in procs)
    return procs


def orm_jobs_col(jobs):
    """
    This is an internal function to take a collection of jobs
    in a variety of formats and return output in the ORM format.
    """
    from pandas import DataFrame
    from epmtlib import isString
    from .models import Job
    if orm_is_query(jobs):
        return jobs
    # empty jobs => select all jobs
    if ((type(jobs) != DataFrame) and not(jobs)):
        return Job.select()

    if type(jobs) == DataFrame:
        jobs = list(jobs['jobid'])

    if isString(jobs):
        if ',' in jobs:
            # jobs a string of comma-separated job ids
            jobs = [ j.strip() for j in jobs.split(",") ]
        else:
            # job is a single jobid, wrap it in a list
            jobs = [jobs]
    if type(jobs) == Job:
        # is it a singular job?
        jobs = [jobs]
    if type(jobs) in [list, set]:
        # jobs is a list of Job objects or a list of jobids or a list of dicts
        # so first convert the dict list to a jobid list
        jobs = [ j['jobid'] if type(j) == dict else j for j in jobs ]

        # now process the list of jobids to make it a list of Job objects
        # keeping in mind that you may already have a job object to begin with
        # Also, remember some jobids may not exist, so don't barf, just skip
        job_objects = []
        for j in jobs:
            if isString(j):
                j = orm_get(Job, j)
                if j is None: continue # job doesn't exist
            job_objects.append(j)
        jobs = job_objects
        # and now convert to a pony Query object so the user can chain
        jobs = Job.select(lambda j: j in jobs)
    return jobs

def orm_to_dict(obj, **kwargs):
    # remove the trigger_post_process key which has no meaning
    # for Pony and is only relevant for SQLA
    if 'trigger_post_process' in kwargs:
        del kwargs['trigger_post_process']
    return obj.to_dict(**kwargs)

def orm_get_procs(jobs, tags, fltr, order, limit, offset, when, hosts, exact_tag_only):
    from .models import Process, Host
    from epmtlib import tags_list, isString
    from datetime import datetime
    if jobs:
        jobs = orm_jobs_col(jobs)
        qs = Process.select(lambda p: p.job in jobs)
    else:
        # no jobs set, so expand the scope to all Process objects
        qs = Process.select()

    # filter using tags if set
    # Remember, tag = {} demands an exact match with an empty dict!
    if tags != None:
        tags = tags_list(tags)
        qs_tags = []
        idx = 0
        tag_query = ''
        for t in tags:
            qst = qs
            qst = _tag_filter(qst, t, exact_tag_only)
            # Important!
            # we are forced to have the modal code below as we want
            # to significantly speed up the common case of a single
            # tag. The slice operator [:] is really slow. We are forced
            # to use it for the case when list contains more than one tag
            # since due to a bug in Pony lazy evaluation of the union query
            # doesn't work.
            qs_tags.append(qst[:] if (len(tags) > 1) else qst)
            tag_query = tag_query + ' or (p in qs_tags[{0}])'.format(idx) if tag_query else '(p in qs_tags[0])'
            idx += 1
        logger.debug('tag filter: {0}'.format(tag_query))
        # read comment marked "Important!" above to understand why
        # we have the modal code below
        qs = qs.filter(tag_query) if (len(tags) > 1) else qs_tags[0]

    # if fltr is a lambda function or a string apply it
    if fltr:
        qs = qs.filter(fltr)

    if when:
        if type(when) == datetime:
            qs = qs.filter(lambda p: p.start <= when and p.end >= when)
        else:
            when_process = Process[when] if isString(when) else when
            qs = qs.filter(lambda p: p.start <= when_process.end and p.end >= when_process.start)

    if hosts:
        if isString(hosts) or (type(hosts) == Host):
            # user probably forgot to wrap in a list
            hosts = [hosts]
        if type(hosts) == list:
            # if the list contains of strings then we want the Host objects
            _hosts = []
            for h in hosts:
                if isString(h):
                    try:
                        h = Host[h]
                    except:
                        continue
                _hosts.append(h)
            hosts = _hosts
        qs = qs.filter(lambda p: p.host in hosts)

    if order:
        qs = qs.order_by(order)

    # finally set limits on the number of processes returned
    if limit:
        qs = qs.limit(int(limit), offset=offset)
    else:
        if offset:
            qs = qs.limit(offset=offset)

    return qs



def orm_get_jobs(qs, tags, fltr, order, limit, offset, when, before, after, hosts, annotations, analyses, exact_tag_only, processed = None):
    from .models import Job, Host
    from epmtlib import tags_list, isString, tag_from_string
    from datetime import datetime

    if fltr:
        qs = qs.filter(fltr)

    # filter using tag if set
    # Remember, tag = {} demands an exact match with an empty dict!
    if tags != None:
        tags = tags_list(tags)
        qs_tags = []
        idx = 0
        tag_query = ''
        for t in tags:
            qst = qs
            qst = _tag_filter(qst, t, exact_tag_only)
            qs_tags.append(qst[:])
            tag_query = tag_query + ' or (j in qs_tags[{0}])'.format(idx) if tag_query else '(j in qs_tags[0])'
            idx += 1
        logger.debug('tag filter: {0}'.format(tag_query))
        qs = qs.filter(tag_query)

    # Remember, annotations = {} demands an exact match with an empty dict!
    if annotations != None:
        if type(annotations) == str:
            annotations = tag_from_string(annotations)
        qs = _annotation_filter(qs, annotations)

    # Remember, analyses = {} demands an exact match with an empty dict!
    if analyses != None:
        if type(analyses) == str:
            analyses = tag_from_string(analyses)
        qs = _analyses_filter(qs, analyses)

    if when:
        if type(when) == datetime:
            qs = qs.filter(lambda j: j.start <= when and j.end >= when)
        else:
            when_job = Job[when] if isString(when) else when
            qs = qs.filter(lambda j: j.start <= when_job.end and j.end >= when_job.start)

    if before != None:
        qs = qs.filter(lambda j: j.end <= before)

    if after != None:
        qs = qs.filter(lambda j: j.start >= after)
                

    if hosts:
        if isString(hosts) or (type(hosts) == Host):
            # user probably forgot to wrap in a list
            hosts = [hosts]
        if type(hosts) == list:
            # if the list contains of strings then we want the Host objects
            _hosts = []
            for h in hosts:
                if isString(h):
                    try:
                        h = Host[h]
                    except:
                        continue
                _hosts.append(h)
            hosts = _hosts
        qs = select(j for j in qs for h in j.hosts if h in hosts)

    if processed is not None:
        qs = _attribute_filter(qs, 'info_dict', {'post_processed': 1 if processed else 0})


    if order:
        qs = qs.order_by(order)

    # finally set limits on the number of jobs returned
    if limit:
        qs = qs.limit(int(limit), offset=offset)
    else:
        if offset:
            qs = qs.limit(offset=offset)

    return qs

def _tag_filter(qs, tag, exact_match):
    return _attribute_filter(qs, 'tags', tag, exact_match)

def _annotation_filter(qs, annotation):
    return _attribute_filter(qs, 'annotations', annotation)

def _analyses_filter(qs, analyses):
    return _attribute_filter(qs, 'analyses', analyses)

# common low-level function to handle dict attribute filters
def _attribute_filter(qs, attr, target, exact_match = False):
    if exact_match or (target == {}):
        qs = qs.filter(lambda j: getattr(j, attr) == target)
    else:
        # we consider a match if the model attribute is a superset
        # of the passed tag
        for (k,v) in target.items():
            qs = qs.filter(lambda j: getattr(j, attr)[k] == v)
    return qs

def orm_get_refmodels(name = None, tag = {}, fltr=None, limit=0, order='', before = None, after = None, exact_tag_only=False):
    from .models import ReferenceModel

    qs = ReferenceModel.select() if (name is None) else ReferenceModel.select().filter(name = name)

    # filter using tag if set
    if tag:
        qs = _tag_filter(qs, tag, exact_tag_only)

    # if fltr is a lambda function or a string apply it
    if fltr:
        qs = qs.filter(fltr)

    if before is not None:
        qs = qs.filter(lambda r: r.created_at <= before)

    if after is not None:
        qs = qs.filter(lambda r: r.created_at >= after)

    if order:
        qs = qs.order_by(order)

    # finally set limits on the number of processes returned
    if limit:
        qs = qs.limit(int(limit))

    return qs

# This function is vulnerable to injection attacks. It's expected that
# the orm API will define a higher-level function to use this
# function after guarding against injection and dangerous sql commands
@db_session
def orm_raw_sql(sql, commit = False):
    logger.debug('Executing: {0}'.format(sql))
    if type(sql) != list:
        sql = [sql]
        try:
            for s in sql:
                res = db.execute(s)
            if commit:
                #trans.commit() ??
                return True
        except:
            logger.warning("Failed raw sql: %s", sql)
            rollback()
            raise
    return res

# convert a url string to a dictionary of parameters
# suitable for establishing a database connection
#
# input: 'postgresql://postgres:example@localhost:5432/EPMT'
# output: {'provider': 'postgres', 'user': 'postgres','password': 'example','host': 'localhost', 'port': 5432, 'dbname': 'EPMT'}
#
# input: 'sqlite:///:memory:'
# output: { 'provider': 'sqlite', 'filename': ':memory:', 'create_db': True }
#
# input: 'sqlite:///db.sqlite'
# output: {'provider': 'sqlite', 'filename':'database.sqlite', 'create_db': True }

def _url2params(url):
    try:
        # sqlite has a different format so we handle it separately
        if 'sqlite' not in url:
            (provider, _, user_host_port, dbname) = url.split('/')
            (user_pass, host_port) = user_host_port.split('@')
            (user, passwd) = user_pass.split(':')
            (host, port) = host_port.split(':')
            port = int(port or 5432)
            provider = provider.replace(':','')
            if provider == 'postgresql':
                provider = 'postgres'
        else:
            filename = url.split('///')[-1]
            return dict(provider='sqlite', filename=filename, create_db=True)
    except:
        raise ValueError('database url ({0}) does not have the right format'.format(url))
    return dict(provider=provider, host=host, port=port, user=user, password=passwd, dbname=dbname)

def orm_dump_schema(show_attributes=True):
    from orm.pony.models import Job, Host, Process, User, ReferenceModel, UnprocessedJob
    retval=[]
    for t in [Job, Host, Process, User, ReferenceModel, UnprocessedJob]:
        if show_attributes:
            print('TABLE {}'.format(t._table_ or t.__name__ or t))
            show(t)
            print('\n')
        else:
            # print(t._table_,t.__name__)
            retval.append(t._table_)
    if not show_attributes:
        return retval
    return True;
