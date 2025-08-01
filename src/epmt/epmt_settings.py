"""
EPMT settings module - loads default settings and user-specific overrides.
"""
# load defaults
from epmt.epmt_default_settings import *

# from logging import getLogger, basicConfig, ERROR
# basicConfig(level=ERROR)
# logger = getLogger(__name__)

# import sys
# logger.debug("attempting import of user settings")
# logger.debug("sys.path entries are:")
# for path in sys.path:
#    logger.debug(f"path={path}")

# now load the user-specific settings.py so they override the defaults
try:
    from epmt.settings import *
except Exception as e:
    raise ModuleNotFoundError('alternate epmt.settings import approach did not' +
                              ' work and neither did the first attempt!') from e
# else:
#    logger.debug('epmt_settings imported successfully! yay!!!')


# epmt_settings_kind=''
# db_params = {'url': 'sqlite:///:memory:', 'echo': False}
