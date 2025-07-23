#!/usr/bin/env python

import os
import unittest
from sys import stderr
from glob import glob
from os import environ, path
from datetime import datetime
from contextlib import nullcontext

import logging
from io import StringIO
from json import loads

import sqlite3
import pandas as pd
import numpy as np


# ok, i kind of see what was happening here.
# might take a bit to tease out but could be worth it for testing fidelity
# i can remove this as the default import for many testing routines one at a time and slowly
# add in the imports theyre actually testing.

from epmt.epmtlib import epmt_logging_init, capture
## ERROR
epmt_logging_init(-1)
## WARNING
#epmt_logging_init(0)
## INFO
#epmt_logging_init(1)
##DEBUG
#epmt_logging_init(2)

import epmt.epmt_settings as settings
import epmt.epmt_query as eq

from epmt.epmt_cmds import epmt_submit
from epmt.epmtlib import timing, get_install_root, get_username, str_dict
from epmt.orm import db_session, setup_db, orm_db_provider, orm_in_memory, Operation

from epmt.orm.sqlalchemy.general import orm_get, orm_dump_schema, orm_commit, orm_is_query
from epmt.orm.sqlalchemy.models import Job, UnprocessedJob, Process

# this will be used repeatedly in the tests, so let's store it
# in a variable instead of repeatedly calling the function
install_root = get_install_root()
