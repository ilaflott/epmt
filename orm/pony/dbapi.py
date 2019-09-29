# DO NOT DO ANY TOP-LEVEL IMPORTS, DO THEM IN THE FUNCTION
# We may import functions from this file as:
# from dbapi import *
# So, not doing top-level imports will prevent needless namespace pollution.

# This file contains a low-level API for direct-access
# to DB-specific information. All the functions below
# rely on the ORM being Pony

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
    """
    from os import environ
    if environ.get('EPMT_USE_DEFAULT_SETTINGS'):
        import epmt_default_settings as settings
    else:
        import settings
    from orm.pony.general import setup_db, _execute_raw_sql
    from logging import getLogger
    logger = getLogger(__name__)
    logger.info("Size of %s\nother args: %s", findwhat, other)
    # Test if provider is supported
    if (settings.db_params.get('provider','') == 'postgres') is False:
        logger.warning("%s Not supported",str(settings.db_params.get('provider','Provider settings key missing')))
        return(False,"")
    # Connect to db for querying
    if setup_db(settings) == False:
        logger.warning("Could Not connect to db")
        return(False,"")
    else:
        logger.info("Connected to db with pony")
    # Json requested 
    if other.json:
        import json
        jsonlist = []
    # Sanitizing user input
    options = ['tablespace', 'table', 'index', 'database']
    cleanList = []
    for test in findwhat:
        cleaner = ''.join(e for e in test if e.isalnum())
        if cleaner.lower() not in options:
            logger.warning("Ignoring %s Not a valid option",cleaner)
        else:
            if cleaner not in cleanList:
                cleanList.append(cleaner)
    every = False
    if len(cleanList) < 1:
        logger.info("Displaying all size results")
        every = True
        cleanList = range(1)
    for arg in cleanList:
        selectables = """SELECT table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE' AND table_schema NOT IN ('pg_catalog', 'information_schema')"""
        try:
            results = _execute_raw_sql(selectables)
            tablelist = [item[0] for item in results]
            if every or arg.lower() == 'database':
                databased = {}
                cmd = 'SELECT pg_database.datname, pg_size_pretty(pg_database_size(pg_database.datname)) AS size FROM pg_database'
                if other.bytes:
                    cmd = 'SELECT pg_database.datname, pg_database_size(pg_database.datname) AS size FROM pg_database'
                if other.json:
                    cmdd = 'SELECT pg_database.datname, pg_database_size(pg_database.datname) AS size FROM pg_database'
                    sizes = _execute_raw_sql(cmdd)
                    for name, size in sizes:
                        databased[name] = int(size)
                    jsonlist.append({"DatabaseSize":databased})
                print("\n ------------------------Database------------------------")
                units = "DB Size"
                if other.bytes:
                    units = units + "(bytes)"
                sizes = _execute_raw_sql(cmd)
                if not sizes:
                    break
                print("{0:40}{1:<20}\n".format("DB Name",units))
                for (name,size) in sizes:
                    print("{0:40}{1:<20}".format(name,size))
        except:
            logger.warning("Db size query failed")

        if every or arg.lower() == 'table':
            print("\n ------------------------Table------------------------")
            units = "Table Size"
            if other.bytes:
                units = units + "(bytes)"
            tabled = {}
            print("{:40}{:<15}{:>15}\n".format("Table",units,"COUNT(*)"))
            try:
                for table in tablelist:
                    cmd = "SELECT pg_size_pretty( pg_total_relation_size(\'"+table+"\') )"
                    if other.bytes:
                        cmd = "SELECT pg_total_relation_size(\'"+table+"\')"
                    if other.json:
                        cmda = "SELECT pg_total_relation_size(\'"+table+"\')"
                        size = _execute_raw_sql(cmda)[0][0]
                        cmda = "SELECT count(*) from \""+table+"\""
                        count = _execute_raw_sql(cmda)[0][0]
                        tabled[table] = {"Size":int(size),"Count":int(count)}
                    size = _execute_raw_sql(cmd)[0][0]
                    cmd = "SELECT count(*) from \""+table+"\""
                    #print (cmd)
                    count = _execute_raw_sql(cmd)[0][0]
                    if not any([count, size]):
                        break
                    #print(count)
                    print("{:40}{:<15}{:>15}".format(table,size,count))
                if other.json:
                    jsonlist.append({"TableSize":tabled})
            except:
                logger.warning("Table size query failed")

        if every or arg.lower() == 'index':
            print("\n ------------------------Index------------------------")
            units = "Index Size"
            if other.bytes:
                units = units + "(bytes)"
            print("{0:40}{1:<20}\n".format("Table",units))
            indexd = {}
            try:
                for table in tablelist:
                    cmd = "SELECT pg_size_pretty( pg_indexes_size(\'"+table+"\') )"
                    if other.json:
                        cmdb = "SELECT pg_indexes_size(\'"+table+"\')"
                        storeit = _execute_raw_sql(cmdb)[0][0]
                        indexd[table] = int(storeit)
                    if other.bytes:
                        cmd = "SELECT pg_indexes_size(\'"+table+"\')"
                    size = _execute_raw_sql(cmd)[0][0]
                    if not size:
                        break
                    print("{0:40}{1:<20}".format(table,size))
                if other.json:
                    jsonlist.append({"IndexSize":indexd})
            except:
                logger.warning("Index size query failed")

        if every or arg.lower() == 'tablespace':
            print("\n ------------------------Tablespace------------------------")
            units = "Size"
            tablespaced = {}
            if other.bytes:
                units = units + "(bytes)"
            print("{0:40}{1:<20}\n".format("Tablespace",units))
            try:
                for tablespace in _execute_raw_sql("SELECT spcname FROM pg_tablespace"):
                    tablespace = tablespace[0]
                    cmd = "SELECT pg_size_pretty( pg_tablespace_size(\'"+str(tablespace)+"\') )"
                    if other.bytes:
                        cmd = "SELECT pg_tablespace_size(\'"+str(tablespace)+"\')"
                    if other.json:
                        cmdd = "SELECT pg_tablespace_size(\'"+str(tablespace)+"\')"
                        size = _execute_raw_sql(cmdd)[0][0]
                        tablespaced[tablespace] = int(size)
                    size = _execute_raw_sql(cmd)[0][0]
                    if not size:
                        break
                    print("{0:40}{1:<20}".format(tablespace,size))
                if other.json:
                    jsonlist.append({"TablespaceSize":tablespaced})
            except:
                logger.warning("Tablespace query failed")
    if other.json:
        if jsonlist:
            import datetime
            current_time = datetime.datetime.utcnow().isoformat()+"Z"
            from pony import __version__ as p_version
            printsettings = settings.db_params.copy()
            printsettings['password'] = "****"
            metadata = {"Generated at:":current_time,
                        "ORM":"Pony "+p_version,
                        "DB Params":printsettings}
            jsonlist.append({"Metadata":metadata})
            print(json.dumps(jsonlist,indent=4))
            return(True, json.dumps(jsonlist))
        else:
            logger.warning("No valid Json")
            return(False, json.dumps(False))
    #print("Index Dict:",indexd, "\nTable Dict(table:size,count):",tabled, "\ntablespace:", tablespaced, "\nDatabase:", databased)
    return(True,"Done")
