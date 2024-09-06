# load defaults
from epmt.epmt_default_settings import *
from logging import getLogger, basicConfig, ERROR
from sys import exit

# now load the user-specific settings.py so they override the defaults
try:
    from settings import *
except Exception as e:
    basicConfig(level=ERROR)
    logger = getLogger(__name__)
    if e.__class__ == ModuleNotFoundError:
        logger.error(str(e)+": attempting relative import instead.")
        from .settings import *
    else:
        raise Exception('an exception other than ModuleNotFoundError?')
finally:
    logger.error('ModuleNotFoundError, damn it!')    
    raise

