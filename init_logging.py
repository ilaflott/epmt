from epmtlib import set_logging
from os import environ

from logging import getLogger
try: logger
except NameError: logger = getLogger(__name__)

if environ.get('EPMT_USE_DEFAULT_SETTINGS'):
    using_default_settings=True
    import epmt_default_settings as settings
else:
    using_default_settings=False
    import settings

# now correct the logging level based on settings.verbose
set_logging(settings.verbose if hasattr(settings, 'verbose') else 0, check=True)
