"""Create table reminders

Revision ID: 1cb55d4fff97
Revises: 3e497f4c9795
Create Date: 2019-02-05 23:15:12.150452

"""
from datetime import datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1cb55d4fff97"
down_revision = "3e497f4c9795"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reminder_content", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, default=datetime.utcnow()),
        sa.Column("trigger_at", sa.DateTime, nullable=False),
        sa.Column("triggered", sa.Boolean, nullable=False),
        sa.Column("playback_channel_id", sa.BigInteger, nullable=False),
    )


def downgrade():
    op.drop_table("reminders")
