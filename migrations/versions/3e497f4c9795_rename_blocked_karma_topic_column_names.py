"""Rename blocked karma topic column names

Revision ID: 3e497f4c9795
Revises: fd2fd5c8960d
Create Date: 2018-04-20 12:28:11.497984

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '3e497f4c9795'
down_revision = 'fd2fd5c8960d'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('blacklist', column_name='name', new_column_name='topic')
    op.alter_column('blacklist', column_name='added_by', new_column_name='user_id')


def downgrade():
    pass
