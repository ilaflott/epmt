from os import environ
import epmt_settings as settings
from .op import *

#
# Below are API calls that have the same implementation on all ORMs
#
def orm_get_or_create(model, **kwargs):
    return (orm_get(model, **kwargs) or orm_create(model, **kwargs))

def orm_db_provider():
    if 'postgres' in settings.db_params.get('url', settings.db_params.get('provider')): return 'postgres'
    if 'sqlite' in settings.db_params.get('url', settings.db_params.get('provider')): return 'sqlite'
    return settings.db_params.get('provider', 'unknown')

def orm_drop_db():
    return setup_db(settings, drop=True)

# return the length of a collection
# For most collections, the len function suffices. However,
# for ORM queries under SQLA, we need to use the count method.
def orm_col_len(c):
    try:
        return len(c)
    except:
        return c.count()

if settings.orm == 'sqlalchemy':
    from .sqlalchemy import *
else:
    from .pony import *

