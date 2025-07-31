#!/usr/bin/env python

# the import below is crucial to get a sane test environment
import unittest
from epmt.orm.sqlalchemy.models import Process
from epmt.orm.sqlalchemy.general import Session, db_session, orm_get, orm_dump_schema, setup_db
from epmt.orm import orm_db_provider
from epmt.epmtlib import timing, capture
import epmt.epmt_settings as settings


@timing
def setUpModule():
    #    print('\n' + str(settings.db_params))
    setup_db(settings)


class EPMTDBSchema(unittest.TestCase):

    # TODO: We need to make this test work for Pony as well
    def test_schema(self):
        with capture() as (out, err):
            retval = orm_dump_schema()
        # print('schema: ', out.getvalue())
        s = out.getvalue()
        # self.assertNotIn('alembic', s)
        self.assertTrue(s.count('TABLE') >= 6)
        # check_output("alembic upgrade head", shell=True)

    # Pony has a bug and only uses 32-bit integers for the PK
    # SQLite doesn't support the ALTER bigint migration. So
    # this test only works for SQLA+PostgreSQL
    @unittest.skipUnless((settings.orm == 'sqlalchemy') and (orm_db_provider()
                         == 'postgres'), 'only works with SQLAlchemy+PostgreSQL')
    @db_session
    def test_process_pk_bigint(self):
        pk_id = 4000000000
        # If the database already has a process with this ID, then we have
        # already passed the test, and we don't need to do anything.
        # Otherwise, we create a Process with the large ID, and save it
        # to the database. Then we retrieve it, and finally delete it.
        if orm_get(Process, id=pk_id) is None:
            p = Process(id=pk_id)
            Session.add(p)
            Session.commit()
            p = Process[pk_id]
            # now clean the just-added record
            Session.delete(p)
            Session.commit()
            with self.assertRaises(KeyError):
                Process[pk_id]


if __name__ == '__main__':
    unittest.main()
