"""create processes staging table for faster ingestion

Revision ID: e703296695bf
Revises: 392efb1132ae
Create Date: 2020-05-21 15:29:37.619437

"""
from alembic import op
import sqlalchemy as sa

# append the directory two-levels above this file
# to the module search path (so we can find the orm module)
import sys
from os.path import dirname
sys.path.append(dirname(__file__) + "/../..")
from orm import orm_db_provider
if orm_db_provider() == 'postgres':
    from sqlalchemy.dialects.postgresql import ARRAY
else:
    from sqlalchemy import ARRAY


# revision identifiers, used by Alembic.
revision = 'e703296695bf'
down_revision = '392efb1132ae'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('processes_staging',
    sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('jobid', sa.String(), nullable=False),
    sa.Column('start', sa.Float(), nullable=False),
    sa.Column('finish', sa.Float(), nullable=False),
    sa.Column('tags', sa.String(), nullable=True),
    sa.Column('host_id', sa.String(), nullable=True),
    sa.Column('threads_df', ARRAY(sa.Float), nullable=True),
    sa.Column('threads_sums', ARRAY(sa.Float), nullable=True),
    sa.Column('numtids', sa.Integer(), nullable=True),
    sa.Column('cpu_time', sa.Float(), nullable=True),
    sa.Column('exename', sa.String(), nullable=True),
    sa.Column('path', sa.String(), nullable=True),
    sa.Column('args', sa.String(), nullable=True),
    sa.Column('pid', sa.Integer(), nullable=True),
    sa.Column('ppid', sa.Integer(), nullable=True),
    sa.Column('pgid', sa.Integer(), nullable=True),
    sa.Column('sid', sa.Integer(), nullable=True),
    sa.Column('gen', sa.Integer(), nullable=True),
    sa.Column('exitcode', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )



def downgrade():
    op.drop_table('processes_staging')
