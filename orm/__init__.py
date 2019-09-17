from os import environ
if environ.get('EPMT_USE_DEFAULT_SETTINGS'):
    import epmt_default_settings as settings
else:   
    import settings


if settings.orm == 'sqlalchemy':
    from .sqlalchemy import *
else:
    from .pony import *

#
# Below are API calls that have the same implementation on all ORMs
#
def orm_get_or_create(model, **kwargs):
    return (orm_get(model, **kwargs) or orm_create(model, **kwargs))
