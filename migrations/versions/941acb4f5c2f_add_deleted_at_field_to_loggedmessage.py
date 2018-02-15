"""Add deleted_at field to LoggedMessage

Revision ID: 941acb4f5c2f
Revises: 8021dc65ebaa
Create Date: 2018-02-15 14:23:03.998153

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '941acb4f5c2f'
down_revision = '8021dc65ebaa'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('messages', sa.Column('deleted_at', sa.DateTime, nullable=True))


def downgrade():
    op.drop_column('messages', 'deleted_at')
