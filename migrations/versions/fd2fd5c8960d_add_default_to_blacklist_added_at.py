"""add default to blacklist added_at

Revision ID: fd2fd5c8960d
Revises: 915998e5c0fc
Create Date: 2018-04-18 10:53:31.819646

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fd2fd5c8960d'
down_revision = '915998e5c0fc'
branch_labels = None
depends_on = None


def upgrade():
    # so Sqlite DOES NOT support ALTER operations so to update columns you gotta do batch updates
    with op.batch_alter_table('blacklist') as batch_op:
        batch_op.alter_column('added_at',nullable=False,server_default=sa.func.current_timestamp())


def downgrade():
    pass