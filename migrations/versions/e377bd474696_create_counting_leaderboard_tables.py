"""Create counting leaderboard tables

Revision ID: e377bd474696
Revises: 2938ed05a881
Create Date: 2021-03-06 01:53:07.454106

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'e377bd474696'
down_revision = '2938ed05a881'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "counting_runs",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("started_at", sa.DateTime, nullable=False),
        sa.Column("ended_at", sa.DateTime, nullable=False),
        sa.Column("length", sa.Integer, nullable=False),
        sa.Column("step", sa.Float, nullable=False)
    )
    op.create_table(
        "counting_users",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("correct_replies", sa.Integer, nullable=False),
        sa.Column("wrong_Replies", sa.Integer, nullable=False)
    )


def downgrade():
    op.drop_table("counting_runs")
    op.drop_table("counting_users")
