# DO NOT DO ANY TOP-LEVEL IMPORTS, DO THEM IN THE FUNCTION
# We may import functions from this file as:
# from dbapi import *
# So, not doing top-level imports will prevent needless namespace pollution.

# This file contains a low-level API for direct-access
# to DB-specific information. All the functions below
# rely on the ORM being Pony

def get_db_size(findwhat, other):
    import settings
    from logging import getLogger
    logger = getLogger(__name__)  # you can use other name
    logger.warning("Pony not yet implemented for db sizing, use sqlalchemy in settings.py")
    return 0
    #from general import xyz
    # If db is 'pg'
    # elif db is sqlite3

    pass

