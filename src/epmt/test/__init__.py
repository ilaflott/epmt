#!/usr/bin/env python
from __future__ import print_function
import unittest
from sys import stderr
from glob import glob
from os import environ
from datetime import datetime
import pandas as pd

from epmt.epmtlib import epmt_logging_init, capture
## ERROR
#epmt_logging_init(-1)
# WARNING
epmt_logging_init(0)
## INFO
#epmt_logging_init(1)
## DEBUG
#epmt_logging_init(2)

import epmt.epmt_settings as settings
import epmt.epmt_query as eq
from epmt.epmt_cmds import epmt_submit
from epmt.epmtlib import *
from epmt.orm import *

# this will be used repeatedly in the tests, so let's store it 
# in a variable instead of repeatedly calling the function
install_root = get_install_root()
