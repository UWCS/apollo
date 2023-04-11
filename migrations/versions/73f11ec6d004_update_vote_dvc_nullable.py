"""update vote dvc nullable

Revision ID: 73f11ec6d004
Revises: ce92ab14f016
Create Date: 2023-04-11 23:17:54.944788

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "73f11ec6d004"
down_revision = "ce92ab14f016"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("discord_vote_choice", schema=None) as batch_op:
        batch_op.alter_column("msg_id", existing_type=sa.BIGINT(), nullable=False)


def downgrade():
    with op.batch_alter_table("discord_vote_choice", schema=None) as batch_op:
        batch_op.alter_column("msg_id", existing_type=sa.BIGINT(), nullable=True)
