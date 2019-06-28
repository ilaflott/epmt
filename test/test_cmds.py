#!/usr/bin/env python
from __future__ import print_function
import unittest
from sys import stderr, exit
from glob import glob
#from pony.orm import db_session
#from models import db
#from pony.orm.core import Query
#import pandas as pd
import datetime

# put this above all epmt imports so they use defaults
from os import environ
environ['EPMT_USE_DEFAULT_SETTINGS'] = "1"

from epmt_job import setup_orm_db
from epmt_cmds import set_logging, epmt_submit
set_logging(-1)
from epmt_cmd_delete import epmt_delete_jobs
from epmt_cmd_list import  epmt_list_jobs
import epmt_query as eq
from epmtlib import timing
import epmt_default_settings as settings

@timing
def setUpModule():
    if settings.db_params.get('filename') != ':memory:':
        print('db_params MUST use in-memory sqlite for testing', file=stderr)
        exit(1)
    setup_orm_db(settings, drop=True)
    datafiles='test/data/query/*.tgz'
    print('\nsetUpModule(EPMTCmds): importing {0}'.format(datafiles))
    epmt_submit(glob(datafiles), dry_run=False)
    
def tearDownModule():
    pass

class EPMTCmds(unittest.TestCase):
    def test_list_jobs(self):
        jobs = eq.get_jobs(fmt='terse')
        self.assertEqual(type(jobs), list, 'wrong jobs format with terse')
        listed_jobs = epmt_list_jobs([])
        self.assertEqual(type(listed_jobs), bool, 'wrong list jobs return type')
        self.assertEqual(listed_jobs, True, 'wrong list jobs return value')
# Currently an exception
#        listed_jobs = epmt_list_jobs(['1234567'])
#        self.assertEqual(listed_jobs, False, 'wrong list of non-existant jobs return value')
        listed_jobs = epmt_list_jobs(['685003', 'fmt=terse'])
        self.assertEqual(listed_jobs, True, 'wrong list job return value with terse and job')
    def test_delete_jobs(self):
        jobs = eq.get_jobs(fmt='terse')
        self.assertEqual(type(jobs), list, 'wrong jobs format with terse')
        self.assertEqual(len(jobs), 3, 'job count in db wrong')
        settings.allow_job_deletion = True
        self.assertEqual(epmt_delete_jobs(['685000']), 1, 'deletion of job failed')
        jobs = eq.get_jobs(fmt='terse')
        self.assertEqual(len(jobs), 2, 'job count in db wrong after delete')

if __name__ == '__main__':
    unittest.main()
