#!/usr/bin/env python

# the import below is crucial to get a sane test environment
import unittest
from os import path
from epmt.epmtlib import capture
from epmt.orm import setup_db, migrate_db, get_db_schema_version, orm_in_memory
import epmt.epmt_settings as settings


def setUpModule():
    #    print('\n' + str(settings.db_params))
    setup_db(settings)


MIGRATION_HEAD = '4ae9a1cac540'


class EPMTDBMigration(unittest.TestCase):
    @unittest.skipUnless((settings.orm == 'sqlalchemy') and not (orm_in_memory()),
                         'requires sqlalchemy with persistent backend')
    def test_baseline_migration(self):
        from epmt.orm import get_db_schema_version
        self.assertEqual(get_db_schema_version(), MIGRATION_HEAD)

    @unittest.skipUnless((settings.orm == 'sqlalchemy') and not (orm_in_memory()),
                         'requires sqlalchemy with persistent backend')
    def test_create_and_apply_migration(self):
        import alembic.config
        from os import path, remove
        rev_id = 'deadbeef'
        migration_file = 'migrations/versions/{}_add_active_column_to_users_table.py'.format(rev_id)
        with capture() as (out, err):
            alembic.config.main(argv=["revision", "--rev-id", rev_id, "-m", "add active column to users table"])
        s = out.getvalue()
        self.assertRegex(s, '.*{}_add_active_column_to_users_table.py .* done'.format(rev_id))
        self.assertTrue(path.isfile(migration_file))
        from epmt.orm import migrate_db, get_db_schema_version
        with capture() as (out, err):
            migrate_db()
        self.assertEqual(get_db_schema_version(), 'deadbeef')
        with capture() as (out, err):
            alembic.config.main(argv=['downgrade', MIGRATION_HEAD])
        self.assertEqual(get_db_schema_version(), MIGRATION_HEAD)
        remove(migration_file)


if __name__ == '__main__':
    unittest.main()
