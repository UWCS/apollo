"""Added vote tables

Revision ID: a146f6ae75a2
Revises: aa6b0d2498fe
Create Date: 2022-03-18 00:46:16.934032

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a146f6ae75a2'
down_revision = 'aa6b0d2498fe'
branch_labels = None
depends_on = None

import enum
class VoteType(enum.Enum):
    basic = 0
    fptp = 1
    approval = 2
    stv = 3
    ranked_pairs = 4

def upgrade():
    op.create_table(
        "vote",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String, nullable=False, server_default="Vote"),
        sa.Column("vote_limit", sa.Integer, nullable=False, server_default="0"),
        sa.Column("ranked_choice", sa.Boolean, nullable=False),
        sa.Column("type", sa.Enum(VoteType), nullable=False),
        sa.Column("seats", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime, nullable=False, default=sa.func.current_timestamp())
    )

    op.create_table(
        "user_vote",
        sa.Column("vote_id", sa.Integer, sa.ForeignKey("vote.id"), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), primary_key=True, nullable=False),
        sa.Column("choice", sa.Integer, sa.ForeignKey("vote_choice.id"), primary_key=True, nullable=False),
        sa.Column("preference", sa.Integer, nullable=False, server_default="0")
    )

    op.create_table(
        "vote_choice",
        sa.Column("vote_id", sa.Integer, sa.ForeignKey("vote.id", ondelete="CASCADE"), primary_key=True, nullable=False),
        sa.Column("choice_index", sa.Integer, primary_key=True, nullable=False),
        sa.Column("choice", sa.String, nullable=False)
    )

    op.create_table(
        "discord_vote_choice",
        sa.Column("vote_id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("choice_index", sa.Integer, primary_key=True, nullable=False),
        sa.Column("emoji", sa.String),
        sa.Column("msg", sa.Integer, sa.ForeignKey("discord_vote_message")),
        op.create_foreign_key("fk_discord_vote_choice_vote_choice", "discord_vote_choice", "vote_choice", ("vote_id", "choice_index"), ("vote_id", "choice_index"))
    )

    op.create_table(
        "discord_vote_message",
        sa.Column("message_id", sa.Integer, primary_key=True),
        sa.Column("channel_id", sa.Integer, nullable=False),
        sa.Column("vote_id", sa.Integer, sa.ForeignKey("discord_vote.id"), sa.ForeignKey("vote.id", ondelete="CASCADE"), nullable=False),
        sa.Column("choices_start_index", sa.Integer, nullable=False),
        sa.Column("numb_choices", sa.Integer, nullable=False, server_default="20"),
        sa.Column("part", sa.Integer, nullable=False)
    )

    op.create_table(
        "discord_vote",
        sa.Column("id", sa.Integer, sa.ForeignKey("vote.id", ondelete="CASCADE"), primary_key=True, nullable=False),
        sa.Column("allowed_role_id", sa.Integer)
    )

def downgrade():
    op.drop_table("vote")
    op.drop_table("user_vote")
    op.drop_table("vote_choice")
    op.drop_table("discord_vote_choice")
    op.drop_table("discord_vote_message")
    op.drop_table("discord_vote")

