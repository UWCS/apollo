"""Added Announcement table

Revision ID: 7c40bda4f1cd
Revises: aa6b0d2498fe
Create Date: 2022-04-29 01:57:51.715343

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7c40bda4f1cd"
down_revision = "aa6b0d2498fe"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "announcements",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("announcement_content", sa.String, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column("trigger_at", sa.DateTime, nullable=False),
        sa.Column("triggered", sa.Boolean, nullable=False),
        sa.Column("playback_channel_id", sa.BigInteger, nullable=False),
        sa.Column("irc_name", sa.String(), nullable=True),
    )


def downgrade():
    op.drop_table("announcements")
