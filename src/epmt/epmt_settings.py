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
        logger.error(str(e)+":install one from preset_settings?")
    else:
        logger.error(str(e))
    raise
    #exit(1) # this breaks pyinstaller, don't do it
