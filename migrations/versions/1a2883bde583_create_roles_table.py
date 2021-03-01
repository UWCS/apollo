"""Create roles table

Revision ID: 1a2883bde583
Revises: eb0c99ae1f63
Create Date: 2020-03-12 22:57:03.326067

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1a2883bde583'
down_revision = 'eb0c99ae1f63'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "role_reaction_messages",
        sa.Column("message_id", sa.BigInteger, primary_key=True),
        sa.Column("channel_id", sa.BigInteger, nullable=False),
        sa.Column("guild_id", sa.BigInteger, nullable=False),
        sa.Column("reaction_name", sa.Unicode(50), nullable=False),
        sa.Column("role_id", sa.BigInteger, nullable=False),
    )


def downgrade():
    op.drop_table("role_reaction_messages")
