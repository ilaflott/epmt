# load defaults
from epmt.epmt_default_settings import *
from logging import getLogger, basicConfig, ERROR
from sys import exit
import sys.path

# now load the user-specific settings.py so they override the defaults
basicConfig(level=ERROR)
logger = getLogger(__name__)
logger.info("attempting import of user settings")
logger.info("sys.path entries are:")
for path in sys.path:
    logger.info(f"path={path}")

try:
    from settings import *
except Exception as e:
    if e.__class__ == ModuleNotFoundError:
        logger.error(str(e)+": attempting epmt.settings import instead.")
        #from .settings import *
        from epmt.settings import *
    else:
        raise Exception('an exception other than ModuleNotFoundError?')
finally:
    logger.error('ModuleNotFoundError, damn it!')    
    raise

