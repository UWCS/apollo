"""empty message

Revision ID: be19cf89389d
Revises: 86fba2709d78
Create Date: 2019-09-06 13:04:28.135494

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'be19cf89389d'
down_revision = '86fba2709d78'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ignored_channels',
        sa.Column('channel', sa.BigInteger, primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('added_at', sa.DateTime, nullable=False, default=sa.func.current_timestamp()),
    )


def downgrade():
    op.drop_table('ignored_channels')
