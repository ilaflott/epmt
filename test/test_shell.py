#!/usr/bin/env python
from __future__ import print_function
import unittest
from sys import stderr, exit
from glob import glob
from os import environ

# put this above all epmt imports
environ['EPMT_USE_DEFAULT_SETTINGS'] = "1"
from epmtlib import set_logging
set_logging(3)

# Put EPMT imports only after we have called set_logging()
import epmt_default_settings as settings
if environ.get('EPMT_USE_SQLALCHEMY'):
    settings.orm = 'sqlalchemy'
    settings.db_params = { 'url': 'sqlite:///:memory:', 'echo': False }
    if environ.get('EPMT_BULK_INSERT'):
        settings.bulk_insert = True

if environ.get('EPMT_USE_PG'):
    settings.db_params = {'provider': 'postgres', 'user': 'postgres','password': 'example','host': 'localhost', 'dbname': 'EPMT'}


from epmtlib import timing, capture
from orm import db_session, setup_db, Job
import epmt_query as eq
from epmt_cmds import epmt_submit
from epmt_cmd_list import  epmt_list_jobs, epmt_list_procs, epmt_list_job_proc_tags, epmt_list_refmodels, epmt_list_op_metrics, epmt_list_thread_metrics


#@timing
#def setUpModule():
#    setup_db(settings)
#    print('\n' + str(settings.db_params))
#    datafiles='test/data/misc/*.tgz'
#    print('setUpModule: importing {0}'.format(datafiles))
#    epmt_submit(glob(datafiles), dry_run=False)
    
#def tearDownModule():

class SHELLCmds(unittest.TestCase):
    def run_cond(self):
        with capture() as (out,err):
            #import argparse, json
            #argns = argparse.Namespace(auto=True, drop=False, dry_run=False, epmt_cmd='dbsize', epmt_cmd_args=['run'], error=False, help=False, jobid=None, json=True, verbose=0)
            from epmt_cmds import epmt_run
            out = epmt_run("1", 'testuser', ["/bin/sleep","1"], wrapit=True, dry_run=False, debug=False)
        self.assertEqual(out, 0, 'run failed')

if __name__ == '__main__':
    unittest.main()
