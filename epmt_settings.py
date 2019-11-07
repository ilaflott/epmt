# load defaults
from epmt_default_settings import *

# now load the user-specific settings.py so they override the defaults
try:
    from settings import *
except ModuleNotFoundError:
    raise ModuleNotFoundError("Could not find settings.py: Please copy a suitable file from preset_settings/* as ./settings.py")
