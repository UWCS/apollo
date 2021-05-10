"""Create table mini_karma_channels

Revision ID: 99d413a94a0a
Revises: 36b213001624
Create Date: 2021-03-01 22:09:44.349012

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "99d413a94a0a"
down_revision = "36b213001624"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mini_karma_channels",
        sa.Column("channel", sa.BigInteger, primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "added_at", sa.DateTime, nullable=False, default=sa.func.current_timestamp()
        ),
    )


def downgrade():
    op.drop_table("mini_karma_channels")
