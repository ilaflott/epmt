# DO NOT DO ANY TOP-LEVEL IMPORTS, DO THEM IN THE FUNCTION
# We may import functions from this file as:
# from dbapi import *
# So, not doing top-level imports will prevent needless namespace pollution.

# This file contains a low-level API for direct-access
# to DB-specific information. All the functions below
# rely on the ORM being Pony

def get_db_size():
    #from general import xyz
    # If db is 'pg'
    # elif db is sqlite3
    pass

