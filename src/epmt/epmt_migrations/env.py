#from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
#fileConfig(config.config_file_name)

# this will overwrite the ini-file sqlalchemy.url path
# with the path given in the config of the main code
# append the parent directory of this test to the module search path
import sys
from os.path import dirname
sys.path.append(dirname(__file__) + "/..") #TODO destroy.

from epmt_settings import db_params
db_url = db_params.get('url', 'sqlite:///:memory:')
# print('INFO  [alembic.runtime.migration] Using {0}'.format(db_url))
config.set_main_option('sqlalchemy.url', db_url)

# add your model's MetaData object here
# for 'autogenerate' support
from orm.sqlalchemy import models
target_metadata = models.Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    # added 'render_as_batch' to allow alter for sqlite
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # added 'render_as_batch' to allow alter for sqlite
        context.configure(
            connection=connection, target_metadata=target_metadata, render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
