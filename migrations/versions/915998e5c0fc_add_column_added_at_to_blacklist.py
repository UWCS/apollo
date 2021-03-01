"""Add column added_at to blacklist

Revision ID: 915998e5c0fc
Revises: 479aac4ff86d
Create Date: 2018-04-17 17:56:51.678960

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '915998e5c0fc'
down_revision = '479aac4ff86d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('blacklist', sa.Column('added_at', sa.DateTime))


def downgrade():
    with op.batch_alter_table('blacklist') as bop:
        bop.drop_column('added_at')
