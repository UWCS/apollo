"""Remove logging

Revision ID: 9b47473d8b90
Revises: 988a71e876c3
Create Date: 2022-12-31 15:45:53.589887

"""
import sqlalchemy as sa
import sqlalchemy_utils as sau
from alembic import op

# revision identifiers, used by Alembic.
revision = "9b47473d8b90"
down_revision = "988a71e876c3"
branch_labels = None
depends_on = None

# https://alembic.sqlalchemy.org/en/latest/batch.html#dropping-unnamed-or-named-foreign-key-constraints
naming_convention = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
}


def upgrade():
    # with op.batch_alter_table("karma_changes") as batch_op:
    #     batch_op.drop_foreign_key("karma_changes_message_id_fkey")
    op.drop_constraint("karma_changes_message_id_fkey", "karma_changes")
    op.drop_table("message_edits")
    op.drop_table("messages")


def downgrade():
    op.create_table(
        "messages",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("message_uid", sa.BigInteger, nullable=False),
        sa.Column("message_content", sau.EncryptedType, nullable=False),
        sa.Column("author", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("channel_name", sau.EncryptedType, nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    
    op.create_table(
        "message_edits",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column(
            "original_message", sa.Integer, sa.ForeignKey("messages.id"), nullable=False
        ),
        sa.Column("new_content", sau.EncryptedType, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    with op.batch_alter_table("karma_changes") as batch_op:
        batch_op.create_foreign_key(
            "fk_karma_changes_messages", "messages", ["message_id"], ["id"]
        )
