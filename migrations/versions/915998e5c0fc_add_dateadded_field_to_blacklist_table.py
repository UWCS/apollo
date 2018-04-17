"""add dateadded field to blacklist table

Revision ID: 915998e5c0fc
Revises: 479aac4ff86d
Create Date: 2018-04-17 17:56:51.678960

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '915998e5c0fc'
down_revision = '479aac4ff86d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('blacklist',
        sa.Column('added_at', sa.DateTime)
    )


def downgrade():
    pass
