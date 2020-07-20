"""use BigInteger for primary key of staging and process table

Revision ID: 4ae9a1cac540
Revises: e703296695bf
Create Date: 2020-07-20 13:10:46.226104

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4ae9a1cac540'
down_revision = 'e703296695bf'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('processes_staging', 'id', existing_type=sa.Integer(), type_=sa.BigInteger())
    op.alter_column('processes', 'id', existing_type=sa.Integer(), type_=sa.BigInteger())

def downgrade():
    op.alter_column('processes_staging', 'id', existing_type=sa.BigInteger(), type_=sa.Integer())
    op.alter_column('processes', 'id', existing_type=sa.BigInteger(), type_=sa.Integer())

