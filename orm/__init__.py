import settings

if settings.orm == 'sqlalchemy':
    from .sqlalchemy import *
else:
    from .pony import *
