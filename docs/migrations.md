# Database Migrations

Migrations are supported for SQLAlchemy at present. We use
alembic for migrations.

### Requirements
 - SQLAlchemy ORM
 - Preferably a database such as Postgres that supports `ALTER`
   SQLite works, but some migrations will give pain as SQLite 
   doesn't support `ALTER`.
 - Persistent database such as in file. We haven't tested
   in-memory configurations.

# Initial DB setup
We have used alembic's auto-generate feature to create a baseline
migration using the model definitions in `orm/sqlalchemy/models.py`.

To achieve the automigration, we had to set `target_metadata` in
`migrations/env.py`, and then run:

```
alembic revision --autogenerate -m "baseline"
```

This created `migrations/versions/392efb1132ae_baseline.py`.

`setup_db` checks and applies this baseline migration if the database
is empty.

Once the database is setup, you can apply migrations as explained below.

### Creating a migration

Let's follow an example that shows how to add a column
to the users table. We will use an SQLite local-file database.

```
# use the appropriate settings template
$ cp settings/settings_sqlite_localfile_sqlalchemy.py settings.py

# now create a migration file
$ alembic revision -m "add admin column to users table"
Generating
  /home/tushar/mm/epmt/build/epmt/migrations/versions/b1cf8c168491_add_admin_column_to_users_table.py ... done

# Now edit the file, and add the following lines to upgrade and downgrade
# functions in the generated file.
def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_admin', sa.Boolean(), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('is_admin')
```

After the migration file has been update, we can run the migration.

```
$ alembic upgrade head
INFO  [alembic.runtime.migration] Using sqlite:///db.sqlite
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> b1cf8c168491, add admin column to users table
```

You can verify the column has been added to the database:
```
$ echo ".schema users" | sqlite3 db.sqlite
CREATE TABLE "users" (
        created_at DATETIME, 
        updated_at DATETIME, 
        name VARCHAR NOT NULL, 
        id INTEGER, 
        info_dict JSON, 
        is_admin BOOLEAN, 
        PRIMARY KEY (name), 
        CHECK (is_admin IN (0, 1)), 
        CHECK (is_admin IN (0, 1)), 
        UNIQUE (id)
);
```

This only adds the column to the database. If you want to the column to be
accessible in the object model, you WILL need to manually update the model
definition in `orm/sqlalchemy/models.py`, and add something like:
```
class User(db.Model):
    ...
    is_admin = db.Column(db.Boolean, default=False)
```

### To remove a migration

To remove the latest migration, simply do:
```
$ alembic downgrade -1
INFO  [alembic.runtime.migration] Using sqlite:///db.sqlite
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running downgrade b1cf8c168491 -> , add admin column to users table
```

You can verify the column has been removed:
```
$ echo ".schema users" | sqlite3 db.sqlite
CREATE TABLE "users" (
        created_at DATETIME, 
        updated_at DATETIME, 
        name VARCHAR NOT NULL, 
        id INTEGER, 
        info_dict JSON, 
        PRIMARY KEY (name), 
        UNIQUE (id)
);
```

To remove all migrations, do:
```
$ alembic downgrade base
```

### References
 - https://medium.com/the-andela-way/alembic-how-to-add-a-non-nullable-field-to-a-populated-table-998554003134
 - https://alembic.sqlalchemy.org/en/latest/batch.html
