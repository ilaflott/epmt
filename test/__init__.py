#!/usr/bin/env python
from __future__ import print_function
import unittest
from sys import stderr, exit
from glob import glob
from os import environ
from datetime import datetime
import pandas as pd

# append the parent directory of this test to the module search path
#from os.path import dirname
#sys.path.append(dirname(__file__) + "/..")

# put this above all epmt imports
environ['EPMT_USE_DEFAULT_SETTINGS'] = "1"
from epmtlib import set_logging, capture
set_logging(-1)

# Put EPMT imports only after we have called set_logging()
import epmt_default_settings as settings
if environ.get('EPMT_USE_SQLALCHEMY'):
    settings.orm = 'sqlalchemy'
    settings.db_params = { 'url': 'sqlite:///:memory:', 'echo': False }
    if environ.get('EPMT_BULK_INSERT'):
        settings.bulk_insert = True

if environ.get('EPMT_USE_PG'):
    dbhost = environ.get('POSTGRES_HOST', 'localhost')
    settings.db_params = { 'url': 'postgresql://postgres:example@{0}:5432/EPMT-TEST'.format(dbhost), 'echo': False } if (settings.orm == 'sqlalchemy') else {'provider': 'postgres', 'user': 'postgres','password': 'example','host': dbhost, 'dbname': 'EPMT-TEST'}

import epmt_query as eq
from epmt_cmds import epmt_submit
from epmtlib import *
from orm import *
