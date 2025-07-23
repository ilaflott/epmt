"""add admin column to users table

Revision ID: 2f96bb1e9bda
Revises:
Create Date: 2019-09-18 09:36:28.650393

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2f96bb1e9bda'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_admin', sa.Boolean(), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('is_admin')
