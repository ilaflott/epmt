#!/usr/bin/env python
from __future__ import print_function
import unittest
from sys import stderr, exit
from glob import glob
from pony.orm import db_session
#from models import db
#from pony.orm.core import Query
#import pandas as pd
import datetime

# put this above all epmt imports so they use defaults
from os import environ
environ['EPMT_USE_DEFAULT_SETTINGS'] = "1"

from epmt_job import setup_orm_db
from epmtlib import timing, set_logging, capture
from epmt_cmds import epmt_submit
from epmt_cmd_delete import epmt_delete_jobs
from epmt_cmd_list import  epmt_list_jobs, epmt_list_procs, epmt_list_job_proc_tags, epmt_list_refmodels, epmt_list_op_metrics, epmt_list_thread_metrics
import epmt_query as eq
import epmt_default_settings as settings
from models import Job

@timing
def setUpModule():
    if settings.db_params.get('filename') != ':memory:':
        print('db_params MUST use in-memory sqlite for testing', file=stderr)
        exit(1)
    set_logging(-1)
    setup_orm_db(settings, drop=False)
    datafiles='test/data/misc/*.tgz'
    print('\nsetUpModule: importing {0}'.format(datafiles))
    epmt_submit(glob(datafiles), dry_run=False)
    
def tearDownModule():
    pass

class EPMTCmds(unittest.TestCase):
    def test_list_jobs(self):
        with capture() as (out,err):
            retval = epmt_list_jobs([])
        self.assertEqual(type(retval), bool, 'wrong list jobs return type')
        self.assertEqual(retval, True, 'wrong list jobs return value')
        with capture() as (out,err):
            retval = epmt_list_jobs(["685000"])
        self.assertEqual(type(retval), bool, 'wrong list jobs return type')
        self.assertEqual(retval, True, 'wrong list jobs return value')
    def test_list_procs(self):
        with capture() as (out,err):
            retval = epmt_list_procs(["685000"])
        self.assertEqual(type(retval), bool, 'wrong list jobs return type')
        self.assertEqual(retval, True, 'wrong list jobs return value')
    def test_list_refmodels(self):
        with capture() as (out,err):
            retval = epmt_list_refmodels([])
        self.assertEqual(retval, False, 'wrong list jobs return value')
    def test_list_op_metrics(self):
        with capture() as (out,err):
            retval = epmt_list_op_metrics([])
        self.assertEqual(type(retval), bool, 'wrong list jobs return type')
        self.assertEqual(retval, True, 'wrong list jobs return value')
    def test_list_thread_metrics(self):
        with capture() as (out,err):
            retval = epmt_list_thread_metrics(["1"])
        self.assertEqual(type(retval), bool, 'wrong list jobs return type')
        self.assertEqual(retval, True, 'wrong list jobs return value')
    def test_list_job_proc_tags(self):
        with capture() as (out,err):
            retval = epmt_list_job_proc_tags(["685000"])
        self.assertEqual(type(retval), bool, 'wrong list jobs return type')
        self.assertEqual(retval, True, 'wrong list jobs return value')


if __name__ == '__main__':
    unittest.main()
