#!/usr/bin/env python

# the import below is crucial to get a sane test environment
from . import *


@timing
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
        self.assertTrue(s.count('TABLE') >= 6)
        #check_output("alembic upgrade head", shell=True)

    # Pony has a bug and only uses 32-bit integers for the PK
    @unittest.skipUnless((settings.orm == 'sqlalchemy'), 'only works with SQLAlchemy')
    @db_session
    def test_process_pk_bigint(self):
        # We save a big integer in the primary key (id) for the Process
        # object. If we haven't applied the bigint migration - '4ae9a1cac540'
        # we will cause an exception when we attempt to save the id to the db
        p = Process(id=4000000000)
        Session.add(p)
        Session.commit()
        p = Process[4000000000]
        # now clean the just-added record
        Session.delete(p)
        Session.commit()
        with self.assertRaises(KeyError): Process[4000000000]




if __name__ == '__main__':
    unittest.main()
