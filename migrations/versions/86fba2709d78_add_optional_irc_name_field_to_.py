"""add optional irc_name field to reminders table

Revision ID: 86fba2709d78
Revises: 1cb55d4fff97
Create Date: 2019-02-07 18:27:29.401466

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '86fba2709d78'
down_revision = '1cb55d4fff97'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('reminders', sa.Column('irc_name', sa.String(), nullable=True))


def downgrade():
    pass
