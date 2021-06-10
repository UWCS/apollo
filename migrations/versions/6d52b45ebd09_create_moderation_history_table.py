"""Create moderation history table

Revision ID: 6d52b45ebd09
Revises: f1e50ee892b4
Create Date: 2021-05-09 19:11:38.752606

"""
import enum

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6d52b45ebd09"
down_revision = "f1e50ee892b4"
branch_labels = None
depends_on = None


@enum.unique
class ModerationAction(enum.Enum):
    """Enum at the time the migration was written"""

    TEMPMUTE = 0
    MUTE = 1
    UNMUTE = 2
    WARN = 3
    REMOVE_WARN = 4
    AUTOWARN = 5
    REMOVE_AUTOWARN = 6
    AUTOMUTE = 7
    REMOVE_AUTOMUTE = 8
    KICK = 9
    TEMPBAN = 10
    BAN = 11
    UNBAN = 12


def upgrade():
    op.create_table(
        "moderation_history",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime,
            nullable=False,
            default=sa.func.current_timestamp(),
        ),
        sa.Column("action", sa.Enum(ModerationAction), nullable=False),
        sa.Column("reason", sa.String, nullable=True),
        sa.Column(
            "moderator_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False
        ),
    )

    op.create_table(
        "moderation_temporary_actions",
        sa.Column(
            "moderation_item_id",
            sa.Integer,
            sa.ForeignKey("moderation_history.id"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "until",
            sa.DateTime,
            nullable=False,
        ),
        sa.Column(
            "complete",
            sa.Boolean,
            nullable=False,
        ),
    )

    op.create_table(
        "moderation_linked_items",
        sa.Column(
            "moderation_item_id",
            sa.Integer,
            sa.ForeignKey("moderation_history.id"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "linked_item",
            sa.Integer,
            sa.ForeignKey("moderation_history.id"),
            nullable=False,
        ),
    )


def downgrade():
    op.drop_table("moderation_temporary_actions")
    op.drop_table("moderation_linked_items")
    op.drop_table("moderation_history")
    bind = op.get_bind()
    sa.Enum(ModerationAction).drop(bind)
