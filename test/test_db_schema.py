#!/usr/bin/env python

# the import below is crucial to get a sane test environment
from . import *

def setUpModule():
    print('\n' + str(settings.db_params))
    setup_db(settings)
    

class EPMTDBSchema(unittest.TestCase):

    # TODO: We need to make this test work for Pony as well
    def test_schema(self):
        with capture() as (out,err):
            retval = orm_dump_schema()
        #print('schema: ', out.getvalue())
        s = out.getvalue()
        #self.assertNotIn('alembic', s)
        self.assertTrue(s.count('TABLE') >= 9)
        #check_output("alembic upgrade head", shell=True)


if __name__ == '__main__':
    unittest.main()
