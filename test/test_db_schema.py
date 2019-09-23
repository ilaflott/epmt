#!/usr/bin/env python
from __future__ import print_function
import unittest
from sys import stderr, exit
from glob import glob
from os import environ
#from subprocess import check_output

# put this above all epmt imports
environ['EPMT_USE_DEFAULT_SETTINGS'] = "1"
from epmtlib import set_logging
set_logging(-1)

# Put EPMT imports only after we have called set_logging()
import epmt_default_settings as settings
settings.orm = 'sqlalchemy'
settings.db_params = { 'url': 'sqlite:///:memory:', 'echo': False }

from epmtlib import capture
from orm import db_session, setup_db, orm_dump_schema
import epmt_query as eq

def setUpModule():
    #remove('db.test')
    setup_db(settings)
    print('\n' + str(settings.db_params))
    

class EPMTDBSchema(unittest.TestCase):
    def test_schema(self):
        with capture() as (out,err):
            retval = orm_dump_schema()
        #print('schema: ', out.getvalue())
        s = out.getvalue()
        self.assertNotIn('alembic', s)
        self.assertEqual(s.count('Table'), 9)
        #check_output("alembic upgrade head", shell=True)


if __name__ == '__main__':
    unittest.main()
