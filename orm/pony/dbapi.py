# DO NOT DO ANY TOP-LEVEL IMPORTS, DO THEM IN THE FUNCTION
# We may import functions from this file as:
# from dbapi import *
# So, not doing top-level imports will prevent needless namespace pollution.

# This file contains a low-level API for direct-access
# to DB-specific information. All the functions below
# rely on the ORM being Pony
from logging import getLogger
logger = getLogger(__name__)
import epmt_logging
import epmt_settings as settings

def get_db_size(findwhat=['database','table','index','tablespace'], usejson=False, usebytes=False):
    """
    Used in finding size of database,tables,index,tablespace storage 
        usage and row count

    Can return both bytes and autosized units determined by database.
        JSON will return if requested.
    get_db_size(['tablespace index database'],usejson=True, usebytes=True)

    findwhat: List of entities to find the size of.  
        Defaults to all options:
        [database, index, table, tablespace]
    
    usejson: Will print and return json values of the 
        requested entities in bytes.

    usebytes: Will query the database for bytes specific datatype.  
        By default the database determines the largest datatype for the size.

    Examples:
    If I want to know the size of only my databases, specify ['database']
        Command Line: ./epmt dbsize database
        Python: get_db_size(['database'])
        ------------------------Database------------------------
        DB Name                                 DB Size             

        postgres                                7677 kB             
        template1                               7537 kB             
        template0                               7537 kB             
        EPMT                                    6857 MB             
        EPMT2                                   3430 MB             
        EPMT-TEST                               23 MB

    If I'm looking for json output of that list of database sizes 
    specify usejson argument.
        Command line: ./epmt dbsize database --json
        Python: get_db_size(['database'],usejson=True)
    ------------------------Database------------------------
    DB Name                                 DB Size             

    postgres                                7677 kB             
    template1                               7537 kB             
    template0                               7537 kB             
    EPMT                                    6857 MB             
    EPMT2                                   3430 MB             
    EPMT-TEST                               23 MB               
    [
        {
            "DatabaseSize": {
                "template1": 7717379,
                "EPMT": 7189926559,
                "postgres": 7860895,
                "EPMT2": 3596923551,
                "EPMT-TEST": 24408735,
                "template0": 7717379
            }
        },
        {
            "Metadata": {
                "Generated at:": "2019-10-03T21:50:42.929178Z",
                "DB Params": {
                    "url": "postgresql://postgres:example@localhost:5432/EPMT",
                    "echo": false,
                    "password": "****"
                }
            }
        }
    ]

    If I'm looking for tablespace and index size in just bytes:
        Command Line: ./epmt dbsize index tablespace --bytes
        Python: get_db_size(['index','tablespace'],usebytes=True)
    ------------------------Index------------------------
    Table                                   Index Size(bytes)   

    hosts                                   16384               
    process                                 49152               
    jobs                                    16384               
    referencemodel                          8192                
    group_user                              16384               
    unprocessed_jobs                        8192                
    user                                    16384               
    job_referencemodel                      16384               
    processes                               181895168           
    users                                   32768               
    unprocessedjob                          8192                
    queue                                   16384               
    process_process                         16384               
    group                                   16384               
    group_job                               16384               
    host_job_associations                   16384               
    host                                    8192                
    ancestor_descendant_associations        197468160           
    job                                     32768               
    refmodel_job_associations               8192                
    refmodels                               8192                
    account                                 16384               
    host_job                                16384               

    ------------------------Tablespace------------------------
    Tablespace                              Size(bytes)         

    pg_default                              10834620034         
    pg_global                               588152

    If I want full output in bytes and json:
        Command Line: ./epmt dbsize --json
        Python: get_db_size(usebytes=True)
    ------------------------Database------------------------
    DB Name                                 DB Size             

    postgres                                7677 kB             
    template1                               7537 kB             
    template0                               7537 kB             
    EPMT                                    6857 MB             
    EPMT2                                   3430 MB             
    EPMT-TEST                               23 MB               

    ------------------------Table-------------------------
    Table                                   Table Size            COUNT(*)

    unprocessed_jobs                        16 kB                        0
    refmodel_job_associations               16 kB                        0
    ...
    host_job_associations                   32 kB                      112
    unprocessedjob                          8192 bytes                   0

    ------------------------Index------------------------
    Table                                   Index Size          

    unprocessed_jobs                        8192 bytes          
    refmodel_job_associations               8192 bytes          
    ...               
    host_job_associations                   16 kB               
    unprocessedjob                          8192 bytes          

    ------------------------Tablespace------------------------
    Tablespace                              Size                

    pg_default                              10 GB               
    pg_global                               574 kB              
    [
        {
            "DatabaseSize": {
                "template0": 7717379,
                "template1": 7717379,
                "postgres": 7860895,
                "EPMT-TEST": 24408735,
                "EPMT2": 3596923551,
                "EPMT": 7189926559
            }
        },
        {
            "TableSize": {
                "unprocessed_jobs": {
                    "Count": 0,
                    "Size": 16384
                }, ....
                "host_job_associations": {
                    "Count": 112,
                    "Size": 32768
                },
                "group": {
                    "Count": 0,
                    "Size": 24576
                }
            }
        },
        {
            "IndexSize": {
                "unprocessed_jobs": 8192,
                "refmodel_job_associations": 8192,
                "job_referencemodel": 16384,
                "jobs": 16384,
                ...
                "host_job_associations": 16384,
                "group": 16384
            }
        },
        {
            "TablespaceSize": {
                "pg_default": 10834620034,
                "pg_global": 588152
            }
        },
        {
            "Metadata": {
                "DB Params": {
                    "echo": false,
                    "url": "postgresql://postgres:example@localhost:5432/EPMT",
                    "password": "****"
                },
                "Generated at:": "2019-10-03T21:59:51.910586Z"
            }
        }
    ]

    """
    from orm.pony.general import setup_db, _execute_raw_sql
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
    if usejson:
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
                if usebytes:
                    cmd = 'SELECT pg_database.datname, pg_database_size(pg_database.datname) AS size FROM pg_database'
                if usejson:
                    cmdd = 'SELECT pg_database.datname, pg_database_size(pg_database.datname) AS size FROM pg_database'
                    sizes = _execute_raw_sql(cmdd)
                    for name, size in sizes:
                        databased[name] = int(size)
                    jsonlist.append({"DatabaseSize":databased})
                print("\n ------------------------Database------------------------")
                units = "DB Size"
                if usebytes:
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
            print("\n ------------------------Table---({})---------------------".format(settings.db_params.get('dbname','nodb')))
            units = "Table Size"
            if usebytes:
                units = units + "(bytes)"
            tabled = {}
            print("{:40}{:<15}{:>15}\n".format("Table",units,"COUNT(*)"))
            try:
                for table in tablelist:
                    cmd = "SELECT pg_size_pretty( pg_total_relation_size(\'"+table+"\') )"
                    if usebytes:
                        cmd = "SELECT pg_total_relation_size(\'"+table+"\')"
                    if usejson:
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
                if usejson:
                    jsonlist.append({"TableSize":tabled})
            except:
                logger.warning("Table size query failed")

        if every or arg.lower() == 'index':
            print("\n ------------------------Index---({})---------------------".format(settings.db_params.get('dbname','nodb')))
            units = "Index Size"
            if usebytes:
                units = units + "(bytes)"
            print("{0:40}{1:<20}\n".format("Table",units))
            indexd = {}
            try:
                for table in tablelist:
                    cmd = "SELECT pg_size_pretty( pg_indexes_size(\'"+table+"\') )"
                    if usejson:
                        cmdb = "SELECT pg_indexes_size(\'"+table+"\')"
                        storeit = _execute_raw_sql(cmdb)[0][0]
                        indexd[table] = int(storeit)
                    if usebytes:
                        cmd = "SELECT pg_indexes_size(\'"+table+"\')"
                    size = _execute_raw_sql(cmd)[0][0]
                    if not size:
                        break
                    print("{0:40}{1:<20}".format(table,size))
                if usejson:
                    jsonlist.append({"IndexSize":indexd})
            except:
                logger.warning("Index size query failed")

        if every or arg.lower() == 'tablespace':
            print("\n ------------------------Tablespace------------------------")
            units = "Size"
            tablespaced = {}
            if usebytes:
                units = units + "(bytes)"
            print("{0:40}{1:<20}\n".format("Tablespace",units))
            try:
                for tablespace in _execute_raw_sql("SELECT spcname FROM pg_tablespace"):
                    tablespace = tablespace[0]
                    cmd = "SELECT pg_size_pretty( pg_tablespace_size(\'"+str(tablespace)+"\') )"
                    if usebytes:
                        cmd = "SELECT pg_tablespace_size(\'"+str(tablespace)+"\')"
                    if usejson:
                        cmdd = "SELECT pg_tablespace_size(\'"+str(tablespace)+"\')"
                        size = _execute_raw_sql(cmdd)[0][0]
                        tablespaced[tablespace] = int(size)
                    size = _execute_raw_sql(cmd)[0][0]
                    if not size:
                        break
                    print("{0:40}{1:<20}".format(tablespace,size))
                if usejson:
                    jsonlist.append({"TablespaceSize":tablespaced})
            except:
                logger.warning("Tablespace query failed")
    if usejson:
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
