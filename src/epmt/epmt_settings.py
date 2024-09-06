# load defaults
from epmt.epmt_default_settings import *
from logging import getLogger, basicConfig, ERROR
import sys


basicConfig(level=ERROR)
logger = getLogger(__name__)
logger.info("attempting import of user settings")
logger.info("sys.path entries are:")
for path in sys.path:
    logger.info(f"path={path}")

# now load the user-specific settings.py so they override the defaults
try: 
    import epmt.settings
    from epmt.settings import *
except Exception as e:
    if e.__class__ == ModuleNotFoundError:
        try:
            import settings
            from settings import *
            logger.error(str(e)+": attempting settings import instead.")
        except Exception as e2
            logger.error('ModuleNotFoundError, damn it!')    
            raise
else:
    logger.info('epmt_settings imported successfully! yay!!!')    


