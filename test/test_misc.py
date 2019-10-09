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

if environ.get('EPMT_USE_PG'):
    settings.db_params = { 'url': 'postgresql://postgres:example@localhost:5432/EPMT-TEST', 'echo': False } if (settings.orm == 'sqlalchemy') else {'provider': 'postgres', 'user': 'postgres','password': 'example','host': 'localhost', 'dbname': 'EPMT'}


from epmtlib import timing, capture
from orm import db_session, setup_db, Job, orm_db_provider
import epmt_query as eq
from epmt_cmds import epmt_submit, epmt_dbsize
from epmt_cmd_delete import epmt_delete_jobs
from epmt_cmd_list import  epmt_list_jobs, epmt_list_procs, epmt_list_job_proc_tags, epmt_list_refmodels, epmt_list_op_metrics, epmt_list_thread_metrics


@timing
def setUpModule():
    setup_db(settings)
    print('\n' + str(settings.db_params))
    datafiles='test/data/misc/685000.tgz'
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

    @unittest.skipIf(orm_db_provider() == 'postgres', 'postgres support requires dbsize PR merge')
    def test_dbsize_provider(self):
        with capture() as (out, err):
            from epmt_cmds import epmt_dbsize
            retval, val = epmt_dbsize()
        isPG = (orm_db_provider() == 'postgres')
        self.assertEqual(retval, isPG, 'wrong database return value')

    @unittest.skip('postgres support requires dbsize PR merge')
    @unittest.skipUnless(orm_db_provider() == 'postgres', 'requires postgres')
    def test_dbsize_json(self):
        with capture() as (out, err):
            import json
            from epmt_cmds import epmt_dbsize
            retval, out = epmt_dbsize(
                ['database', 'table', 'index', 'tablespace'], usejson=True)
            throws = True
            json.loads(out)
            if len(out) > 1:
                throws = False
        self.assertEqual(throws, False, 'JSON not loaded successfully')

if __name__ == '__main__':
    unittest.main()
