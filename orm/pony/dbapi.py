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

    Returns:
    if json=True
        return json
    else 
        return 0
    """
    import settings
    from general import setup_db,_execute_raw_sql
    from epmt_cmds import PrintFail
    from logging import getLogger
    logger = getLogger(__name__)  # you can use other name
    #logger.warning("Pony not yet implemented for db sizing, use sqlalchemy in settings.py")
    import settings
    logger.info("Findwhat %s\nother: %s", findwhat, other)
    # ignore settings
    if setup_db(settings) == False:
        PrintFail()
        logger.warn("Could Not connect to db")
        return False
    logger.info("Connected to db with pony")
    if other.json:
        import json
        jsonlist = []
    #Sanitizing
    options = ['tablespace', 'table', 'index', 'database']
    cleanList = []
    for test in findwhat:
        cleaner = ''.join(e for e in test if e.isalnum())
        if cleaner.lower() not in options:
            logger.warn("Ignoring %s Not a valid option",cleaner)
        else:
            if cleaner not in cleanList:
                cleanList.append(cleaner)
    logger.info("epmt dbsize: %s",str(findwhat))
    every = False
    print(settings.db_params)
    
    if (settings.db_params.get('provider','') == "postgres") is False:
        logger.warn("%s Not supported",str(settings.db_params.get('provider','Provider settings key missing')))
        return False

    if setup_db(settings) == False:
        PrintFail()
        logger.warn("Could Not connect to db")
        return False
    if len(cleanList) < 1:
        logger.info("Displaying all options")
        every = True
        cleanList = range(1)
    for arg in cleanList:
        selectables = """SELECT table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE' AND table_schema NOT IN ('pg_catalog', 'information_schema')"""
        results = _execute_raw_sql(selectables)
        print(results)
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
                    databased.setdefault(str(name),[]).append(int(size))
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

        if every or arg.lower() == 'table':
            print("\n ------------------------Table------------------------")
            units = "Table Size"
            if other.bytes:
                units = units + "(bytes)"
            tabled = {}
            print("{:40}{:<15}{:>15}\n".format("Table",units,"COUNT(*)"))
            try:
                print(tablelist)
                for table in tablelist:
                    cmd = "SELECT pg_size_pretty( pg_total_relation_size(\'"+table+"\') )"
                    if other.bytes:
                        cmd = "SELECT pg_total_relation_size(\'"+table+"\')"
                    if other.json:
                        cmda = "SELECT pg_total_relation_size(\'"+table+"\')"
                        size = _execute_raw_sql(cmda)[0][0]
                        cmda = "SELECT count(*) from \""+table+"\""
                        count = _execute_raw_sql(cmda)[0][0]
                        tabled[table] = (int(size),int(count))
                    size = _execute_raw_sql(cmd)[0][0]
                    cmd = "SELECT count(*) from \""+table+"\""
                    #print (cmd)
                    count = _execute_raw_sql(cmd)[0][0]
                    if not any([count, size]):
                        break
                    #print(count)
                    print("{:40}{:<15}{:>15}".format(table,size,count))
            except:
                raise
                PrintFail()
                return 1
            if other.json:
                jsonlist.append({"TableSize":tabled})
        if every or arg.lower() == 'index':
            print("\n ------------------------Index------------------------")
            units = "Index Size"
            if other.bytes:
                units = units + "(bytes)"
            print("{0:40}{1:<20}\n".format("Table",units))
            indexd = {}
            for table in tablelist:
                cmd = "SELECT pg_size_pretty( pg_indexes_size(\'"+table+"\') )"
                try:
                    if other.json:
                        cmdb = "SELECT pg_indexes_size(\'"+table+"\')"
                        storeit = _execute_raw_sql(cmdb)[0][0]
                        indexd[table] = int(storeit)
                    if other.bytes:
                        cmd = "SELECT pg_indexes_size(\'"+table+"\')"
                    size = _execute_raw_sql(cmd)[0][0]
                except:
                    PrintFail()
                    return 1
                if not size:
                    break
                print("{0:40}{1:<20}".format(table,size))
            if other.json:
                jsonlist.append({"IndexSize":indexd})
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
                PrintFail()
                return 1
    if other.json:
        return(json.dumps(jsonlist, indent=4))
    #print("Index Dict:",indexd, "\nTable Dict(table:size,count):",tabled, "\ntablespace:", tablespaced, "\nDatabase:", databased)
    return True