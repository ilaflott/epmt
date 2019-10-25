from epmtlib import set_logging
from sys import stderr, exit
# from logging import getLogger
# get the calling module name so we can give it to logger
# try:
#     import inspect 
#     frm = inspect.stack()[1]
#     print(frm)
#     mod = inspect.getmodule(frm[0])
#     print(mod)
#     logger = getLogger(mod)
# except NameError: 
#     logger = getLogger(__name__)

import epmt_settings as settings

# now correct the logging level based on settings.verbose
set_logging(settings.verbose if hasattr(settings, 'verbose') else 0, check=True)
