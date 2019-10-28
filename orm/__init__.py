from os import environ
import epmt_settings as settings

if settings.orm == 'sqlalchemy':
    from .sqlalchemy import *
else:
    from .pony import *

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
