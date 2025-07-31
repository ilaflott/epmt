from os import environ
import epmt.epmt_settings as settings
from .op import Operation

#
# Below are API calls that have the same implementation on all ORMs
#

# Note, the function below is not ATOMIC! There is a potential
# for a race condition here.


def orm_get_or_create(model, **kwargs):
    return (orm_get(model, **kwargs) or orm_create(model, **kwargs))


def orm_db_provider():
    if 'postgres' in settings.db_params.get('url', settings.db_params.get('provider')):
        return 'postgres'
    if 'sqlite' in settings.db_params.get('url', settings.db_params.get('provider')):
        return 'sqlite'
    return settings.db_params.get('provider', 'unknown')


def orm_in_memory():
    return 'memory' in settings.db_params.get('url', settings.db_params.get('provider'))


def orm_drop_db():
    return setup_db(settings, drop=True)


def orm_sql(sql):
    return orm_raw_sql(sql)

# return the length of a collection
# For most collections, the len function suffices. However,
# for ORM queries under SQLA, we need to use the count method.


def orm_col_len(c):
    try:
        return len(c)
    except BaseException:
        return c.count()


def orm_db_size(findwhat=['database', 'table', 'index', 'tablespace'], usejson=True, usebytes=True):
    """
    Print size of database,tables,index,tablespace storage and row count

    findwhat: List of entities to find the size of, default is [database, index, table, tablespace]
    usejson: Printed in JSON, default.
    usebytes: All data reported in bytes, default.

    """
#    from orm import orm_db_provider, orm_dump_schema, orm_sql, setup_db
    from sys import exc_info
    from datetime import datetime
    from json import dumps

    # Test if provider is supported
    provider = orm_db_provider()
    if provider != 'postgres':
        logger.warning("%s not supported for dbsize", provider)
        return (False)

    if setup_db(settings) == False:
        logger.error("Could not connect to db")
        return (False)

    struct = {}
    for arg in findwhat:
        if arg == 'database':
            databased = {}
            cmd = 'SELECT pg_database.datname, pg_database_size(pg_database.datname) AS size FROM pg_database'
            try:
                sizes = orm_sql(cmd)
                for name, size in sizes:
                    databased[name] = int(size)
                    logger.debug("database[%s]=%d", name, int(size))
                struct[arg] = databased
            except BaseException:
                e = exc_info()[0]
                logger.warning("DB size query failed: %s" % e)

        if arg == 'table':
            tabled = {}
            for table in orm_dump_schema(show_attributes=False):
                cmd = "SELECT pg_total_relation_size(\'" + table + "\')"
                size = orm_sql(cmd).fetchall()[0][0]
                cmd = "SELECT count(*) from \"" + table + "\""
                count = orm_sql(cmd).fetchall()[0][0]
                tabled[table] = [int(size), int(count)]
                logger.debug("table[%s]=[%d,%d]", table, int(size), int(count))
                struct[arg] = tabled
#            except:
#                e = exc_info()[0]
#                logger.warning("Table size query failed: %s" % e )

        if arg == 'index':
            indexd = {}
            try:
                for table in orm_dump_schema(show_attributes=False):
                    cmd = "SELECT pg_indexes_size(\'" + table + "\')"
                    size = orm_sql(cmd).fetchone()[0]
                    indexd[table] = int(size)
                    logger.debug("index[%s]=%d", table, int(size))
                struct[arg] = indexd
            except BaseException:
                e = exc_info()[0]
                logger.warning("Index size query failed: %s" % e)

        if arg == 'tablespace':
            tablespaced = {}
            try:
                tablespaces = orm_sql("SELECT spcname FROM pg_tablespace")
                for tablespace in tablespaces:
                    tablespace = tablespace[0]
                    cmd = "SELECT pg_tablespace_size(\'" + str(tablespace) + "\')"
                    size = orm_sql(cmd).fetchall()[0][0]
                    tablespaced[tablespace] = int(size)
                    logger.debug("tablespace[%s]=%d", tablespace, int(size))
                struct[arg] = tablespaced
            except BaseException:
                e = exc_info()[0]
                logger.warning("Tablespace size query failed: %s" % e)

    current_time = datetime.utcnow().isoformat() + "Z"
    printsettings = {}
    printsettings["orm"] = settings.orm
    printsettings.update(settings.db_params)
    struct["timestamp"] = current_time
    struct["settings"] = printsettings
    if not usejson:
        print(struct)
    else:
        print(dumps(struct, indent=4))
    return (True)


if settings.orm == 'sqlalchemy':
    from .sqlalchemy import (
        Base, Session, db_session, setup_db, orm_get, orm_findall, orm_create, orm_delete,
        orm_delete_jobs, orm_delete_refmodels, orm_commit, orm_add_to_collection,
        orm_sum_attribute, orm_is_query, orm_procs_col, orm_jobs_col, orm_to_dict,
        orm_get_procs, orm_get_jobs, orm_get_refmodels, orm_dump_schema, orm_raw_sql,
        check_and_apply_migrations, migrate_db, alembic_dump_schema,
        CommonMeta, User, Host, ReferenceModel, Job, UnprocessedJob, Process,
        refmodel_job_associations_table, host_job_associations_table,
        ancestor_descendant_associations_table
    )
else:
    from .pony import (
        Base, Session, db_session, setup_db, orm_get, orm_findall, orm_create, orm_delete,
        orm_delete_jobs, orm_delete_refmodels, orm_commit, orm_add_to_collection,
        orm_sum_attribute, orm_is_query, orm_procs_col, orm_jobs_col, orm_to_dict,
        orm_get_procs, orm_get_jobs, orm_get_refmodels, orm_dump_schema, orm_raw_sql,
        check_and_apply_migrations, migrate_db, alembic_dump_schema,
        CommonMeta, User, Host, ReferenceModel, Job, UnprocessedJob, Process,
        refmodel_job_associations_table, host_job_associations_table,
        ancestor_descendant_associations_table
    )
