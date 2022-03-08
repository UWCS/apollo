"""Update default datetime columns to the current time rather than start time

Revision ID: 2938ed05a881
Revises: 99d413a94a0a
Create Date: 2021-03-05 21:00:30.275821

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2938ed05a881"
down_revision = "99d413a94a0a"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("reminders") as bop:
        bop.alter_column("created_at", server_default=sa.func.current_timestamp())
    with op.batch_alter_table("users") as bop:
        bop.alter_column("first_seen", server_default=sa.func.current_timestamp())
        bop.alter_column("last_seen", server_default=sa.func.current_timestamp())
    with op.batch_alter_table("karma") as bop:
        bop.alter_column("added", server_default=sa.func.current_timestamp())


def downgrade():
    with op.batch_alter_table("reminders") as bop:
        bop.alter_column("created_at", server_default=None)
    with op.batch_alter_table("users") as bop:
        bop.alter_column("first_seen", server_default=None)
        bop.alter_column("last_seen", server_default=None)
    with op.batch_alter_table("karma") as bop:
        bop.alter_column("added", server_default=None)
