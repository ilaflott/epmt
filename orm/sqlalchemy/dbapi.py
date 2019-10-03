# DO NOT DO ANY TOP-LEVEL IMPORTS, DO THEM IN THE FUNCTION
# We may import functions from this file as:
# from dbapi import *
# So, not doing top-level imports will prevent needless namespace pollution.

# This file contains a low-level API for direct-access
# to DB-specific information. All the functions below
# rely on the ORM being sqlalchemy

def get_db_size(findwhat, other):
    """
    Used in finding size of database,tables,index,tablespace storage usage and row count
    
    Can return both bytes and autosized units determined by database.  JSON will return if requested.
    get_db_size('tablespace index database',[other.json=True, other.bytes=True])
    
    Parameters:
    findwhat string: Options include database, table, index, tablespace or epmty string
    
    other args: arg parser arguments from epmt command
        bytes & json are utilized from this list
        Namespace(auto=False, bytes=False, dbsize=True, drop=False, 
            dry_run=False, epmt_cmd='dbsize', epmt_cmd_args=[], error=False, 
            help=False, jobid=None, json=False, verbose=0)

    Returns:
    if settings provider is not postgres
        return(False,)
    if json=True
        return(True,json)
    else 
        return(True,)
    """
    from os import environ
    if environ.get('EPMT_USE_DEFAULT_SETTINGS'):
        import epmt_default_settings as settings
    else:
        import settings
    from orm.sqlalchemy.general import _execute_raw_sql
    from sqlalchemy import exc
    from logging import getLogger
    logger = getLogger(__name__)  # you can use other name
    import init_logging
    # Test if provider is supported
    if settings.db_params.get('url', '').startswith('postgresql://') is False:
        logger.warning("%s is not supported", settings.db_params.get('url', ''))
        return(False,"Not supported")
    if other.json:
        import json
        jsonlist = []
    #Sanitizing
    options = ['tablespace', 'table', 'index', 'database']
    cleanList = []
    for test in findwhat:
        cleaner = ''.join(e for e in test if e.isalnum())
        if cleaner.lower() not in options:
            logger.warning("Ignoring %s Not a valid option",cleaner)
        else:
            if cleaner not in cleanList:
                cleanList.append(cleaner)
    logger.info("epmt dbsize: %s",str(findwhat))
    every = False
    # Load ORM and Connect to DB for query
    try:
        from orm import orm_dump_schema, setup_db
    except (ImportError, Exception) as e:
        raise
        logger.warning("Could Not connect to orm")
        return(False,"Not connected")
    try:
        if setup_db(settings) == False:
            logger.warning("Could Not connect to db")
            return(False,"Not connected")
    except exc.SQLAlchemyError as e:
        logger.warning("Could Not connect to db"+str(e))
        return(False,"Not connected")
    if len(cleanList) < 1:
        logger.info("Displaying all options")
        every = True
        cleanList = range(1)
    for arg in cleanList:
        if every or arg.lower() == 'database':
            databased = {}
            cmd = 'SELECT pg_database.datname, pg_size_pretty(pg_database_size(pg_database.datname)) AS size FROM pg_database'
            if other.bytes:
                cmd = 'SELECT pg_database.datname, pg_database_size(pg_database.datname) AS size FROM pg_database'
            if other.json:
                cmdd = 'SELECT pg_database.datname, pg_database_size(pg_database.datname) AS size FROM pg_database'
                try:
                    sizes = _execute_raw_sql(cmdd)
                    for name, size in sizes:
                        databased[name]=size
                    jsonlist.append({"DatabaseSize":databased})
                except exc.SQLAlchemyError:
                    logger.warning("Db size query failed")

            print("\n ------------------------Database------------------------")
            units = "DB Size"
            if other.bytes:
                units = units + "(bytes)"
            try:
                sizes = _execute_raw_sql(cmd)
                if not sizes:
                    break
                print("{0:40}{1:<20}\n".format("DB Name",units))
                for (name,size) in sizes:
                    print("{0:40}{1:<20}".format(name,size))
            except exc.SQLAlchemyError:
                logger.warning("Db size query failed")

        if every or arg.lower() == 'table':
            print("\n ------------------------Table------------------------")
            units = "Table Size"
            if other.bytes:
                units = units + "(bytes)"
            tabled = {}
            print("{:40}{:<15}{:>15}\n".format("Table",units,"COUNT(*)"))
            try:
                for table in orm_dump_schema(show_attributes = False):
                    cmd = "SELECT pg_size_pretty( pg_total_relation_size(\'"+table+"\') )"
                    if other.bytes:
                        cmd = "SELECT pg_total_relation_size(\'"+table+"\')"
                    if other.json:
                        cmda = "SELECT pg_total_relation_size(\'"+table+"\')"
                        size = _execute_raw_sql(cmda).fetchall()[0][0]
                        cmda = "SELECT count(*) from \""+table+"\""
                        count = _execute_raw_sql(cmda).fetchall()[0][0]
                        tabled[table] = {"Size":int(size),"Count":int(count)}
                    size = _execute_raw_sql(cmd).fetchall()[0][0]
                    cmd = "SELECT count(*) from \""+table+"\""
                    #print (cmd)
                    count = _execute_raw_sql(cmd).fetchall()[0][0]
                    if not any([count, size]):
                        break
                    #print(count)
                    print("{:40}{:<15}{:>15}".format(table,size,count))
                if other.json:
                    jsonlist.append({"TableSize":tabled})
            except exc.SQLAlchemyError:
                logger.warning("Table query failed")

        if every or arg.lower() == 'index':
            print("\n ------------------------Index------------------------")
            units = "Index Size"
            if other.bytes:
                units = units + "(bytes)"
            print("{0:40}{1:<20}\n".format("Table",units))
            indexd = {}
            try:
                for table in orm_dump_schema(show_attributes = False):
                    cmd = "SELECT pg_size_pretty( pg_indexes_size(\'"+table+"\') )"
                    if other.json:
                        cmdb = "SELECT pg_indexes_size(\'"+table+"\')"
                        storeit = _execute_raw_sql(cmdb).fetchone()[0]
                        indexd[table] = int(storeit)
                    if other.bytes:
                        cmd = "SELECT pg_indexes_size(\'"+table+"\')"
                    size = _execute_raw_sql(cmd).fetchone()[0]
                    if not size:
                        break
                    print("{0:40}{1:<20}".format(table,size))
                if other.json:
                    jsonlist.append({"IndexSize":indexd})
            except exc.SQLAlchemyError:
                logger.warning("Index query failed")

        if every or arg.lower() == 'tablespace':
            print("\n ------------------------Tablespace------------------------")
            units = "Size"
            tablespaced = {}
            if other.bytes:
                units = units + "(bytes)"
            print("{0:40}{1:<20}\n".format("Tablespace",units))
            try:
                tablespaces = _execute_raw_sql("SELECT spcname FROM pg_tablespace")
                for tablespace in tablespaces:
                    tablespace = tablespace[0]
                    cmd = "SELECT pg_size_pretty( pg_tablespace_size(\'"+str(tablespace)+"\') )"
                    if other.bytes:
                        cmd = "SELECT pg_tablespace_size(\'"+str(tablespace)+"\')"
                    if other.json:
                        cmdd = "SELECT pg_tablespace_size(\'"+str(tablespace)+"\')"
                        size = _execute_raw_sql(cmdd).fetchall()[0][0]
                        tablespaced[tablespace] = int(size)
                    size = _execute_raw_sql(cmd).fetchall()[0][0]
                    if not size:
                        break
                    print("{0:40}{1:<20}".format(tablespace,size))
                if other.json:
                    jsonlist.append({"TablespaceSize":tablespaced})
            except exc.SQLAlchemyError:
                logger.warning("Tablespace query failed")

    if other.json:
        if jsonlist:
            import datetime
            current_time = datetime.datetime.utcnow().isoformat()+"Z"
            from sqlalchemy import __version__ as sa_version
            printsettings = settings.db_params.copy()
            printsettings['password'] = "****"
            metadata = {"Generated at:":current_time,
                        "DB Params":printsettings}
            jsonlist.append({"Metadata":metadata})
            print(json.dumps(jsonlist,indent=4))
            return(True, json.dumps(jsonlist))
        else:
            logger.warning("No valid Json")
            return(False, json.dumps(False))

