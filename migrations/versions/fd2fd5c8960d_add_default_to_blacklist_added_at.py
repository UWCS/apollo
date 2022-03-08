"""add default to blacklist added_at

Revision ID: fd2fd5c8960d
Revises: 915998e5c0fc
Create Date: 2018-04-18 10:53:31.819646

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "fd2fd5c8960d"
down_revision = "915998e5c0fc"
branch_labels = None
depends_on = None


def upgrade():
    # Sqlite DOES NOT support ALTER operations so to update columns you have to do batch updates
    with op.batch_alter_table("blacklist") as batch_op:
        batch_op.alter_column(
            "added_at", nullable=False, server_default=sa.func.current_timestamp()
        )


def downgrade():
    with op.batch_alter_table("blacklist") as bop:
        bop.alter_column("added_at", nullable=True, server_default=None)
