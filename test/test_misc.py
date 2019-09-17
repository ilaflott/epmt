#!/usr/bin/env python
from __future__ import print_function
import unittest
from sys import stderr, exit
from glob import glob
from os import environ

# put this above all epmt imports
environ['EPMT_USE_DEFAULT_SETTINGS'] = "1"
from epmtlib import set_logging
set_logging(-1)

# Put EPMT imports only after we have called set_logging()
import epmt_default_settings as settings
if environ.get('EPMT_USE_SQLALCHEMY'):
    settings.orm = 'sqlalchemy'
    settings.db_params = { 'url': 'sqlite:///:memory:', 'echo': False }
    if environ.get('EPMT_BULK_INSERT'):
        settings.bulk_insert = True

from epmtlib import timing, capture
from orm import db_session, setup_db, Job
import epmt_query as eq
from epmt_cmds import epmt_submit, epmt_dbsize
from epmt_cmd_delete import epmt_delete_jobs
from epmt_cmd_list import  epmt_list_jobs, epmt_list_procs, epmt_list_job_proc_tags, epmt_list_refmodels, epmt_list_op_metrics, epmt_list_thread_metrics


@timing
def setUpModule():
    setup_db(settings)
    print('\n' + str(settings.db_params))
    datafiles='test/data/misc/*.tgz'
    print('setUpModule: importing {0}'.format(datafiles))
    epmt_submit(glob(datafiles), dry_run=False)
    
#def tearDownModule():

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
            retval = epmt_list_refmodels('')
        self.assertEqual(retval, False, 'wrong list jobs return value')
    def test_list_op_metrics(self):
        with capture() as (out,err):
            retval = epmt_list_op_metrics(['685000'])
        self.assertTrue(retval, 'wrong list op_metrics return type')
    def test_list_thread_metrics(self):
        p = eq.root('685000', fmt='terse')
        self.assertTrue(p, 'empty root process')
        with capture() as (out,err):
            retval = epmt_list_thread_metrics([p])
        self.assertEqual(type(retval), bool, 'wrong list jobs return type')
        self.assertEqual(retval, True, 'wrong list jobs return value')
    def test_list_job_proc_tags(self):
        with capture() as (out,err):
            retval = epmt_list_job_proc_tags(["685000"])
        self.assertEqual(type(retval), bool, 'wrong list jobs return type')
        self.assertEqual(retval, True, 'wrong list jobs return value')

    def test_dbsize(self):
        with capture() as (out,err):
            import argparse
            argns = argparse.Namespace(auto=False, bytes=False, dbsize=True, drop=False, dry_run=False, epmt_cmd='dbsize', epmt_cmd_args=['database', 'table'], error=False, help=False, jobid=None, json=False, verbose=0)
            from epmt_cmds import epmt_dbsize
            retval = epmt_dbsize('',argns)
            isNotSqlite = (settings.db_params.get('provider', '') == "postgres")
            #print("conditional equals:",isNotSqlite)
            #print("response:",retval)
        self.assertEqual(retval, isNotSqlite, 'wrong database return value')

if __name__ == '__main__':
    unittest.main()
