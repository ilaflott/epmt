# /models/__init__.py
#from pony import orm
#from .general import db
import settings

if settings.orm == 'sqlalchemy':
    from .sqlalchemy import *
else:
    from .pony import *

#from .logical_model import *
#from .measurement_model import *
