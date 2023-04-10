"""Fix various bits

Revision ID: ce92ab14f016
Revises: 9b47473d8b90
Create Date: 2023-04-10 12:05:25.996003

"""
import sqlalchemy as sa
import sqlalchemy_utils as sau
from alembic import op

# revision identifiers, used by Alembic.
revision = "ce92ab14f016"
down_revision = "9b47473d8b90"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = sa.engine.reflection.Inspector(bind)
    tables = inspector.get_table_names()

    with op.batch_alter_table(
        "karma_changes", schema=None
    ) as batch_op:
        batch_op.alter_column("message_id", existing_type=sa.BIGINT(), nullable=False)
        batch_op.drop_column("mid_old")

    # Drop if existing
    if "message_edits" in tables:
        op.drop_table("message_edits")
    if "messages" in tables:
        op.drop_table("messages")

    with op.batch_alter_table(
        "user_vote", schema=None
    ) as batch_op:
        batch_op.create_foreign_key(
            "fk_user_vote_vote_id_vote_choice",
            "vote_choice",
            ["vote_id", "choice"],
            ["vote_id", "choice_index"],
            ondelete="CASCADE",
        )


def downgrade():
    with op.batch_alter_table(
        "user_vote", schema=None
    ) as batch_op:
        batch_op.drop_constraint("fk_user_vote_vote_id_vote_choice", type_="foreignkey")

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer, primary_key=True, nullable=False),
        sa.Column("message_uid", sa.BigInteger, nullable=False),
        sa.Column("message_content", sau.EncryptedType, nullable=False),
        sa.Column("author", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("channel_name", sau.EncryptedType, nullable=False),
        sa.Column("deleted_at", sa.DateTime, nullable=False),
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
    
    # with op.batch_alter_table(
    #     "karma_changes", schema=None
    # ) as batch_op:
    #     batch_op.add_column(sa.Column("mid_old", sa.Integer, nullable=True))
    #     batch_op.alter_column("message_id", existing_type=sa.BIGINT(), nullable=True)
    
    op.drop_table("karma_changes")
    op.create_table(
        "karma_changes",
        sa.Column("karma_id", sa.Integer, sa.ForeignKey("karma.id")),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("mid_old", sa.Integer, sa.ForeignKey("messages.id")),
        sa.Column("message_id", sa.BigInteger),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("change", sa.Integer, nullable=False),
        sa.Column("score", sa.Integer, nullable=False),
        sa.Column("reason", sa.String, nullable=True),
        sa.PrimaryKeyConstraint("karma_id", "user_id", "message_id")
    )