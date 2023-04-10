"""Fix various bits

Revision ID: ce92ab14f016
Revises: 9b47473d8b90
Create Date: 2023-04-10 12:05:25.996003

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ce92ab14f016"
down_revision = "9b47473d8b90"
branch_labels = None
depends_on = None

# https://alembic.sqlalchemy.org/en/latest/batch.html#dropping-unnamed-or-named-foreign-key-constraints
nc = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "%(table_name)s_pkey",
}


def upgrade():
    bind = op.get_bind()
    inspector = sa.engine.reflection.Inspector(bind)
    tables = inspector.get_table_names()

    with op.batch_alter_table(
        "karma_changes", schema=None, naming_convention=nc
    ) as batch_op:
        batch_op.alter_column("message_id", existing_type=sa.BIGINT(), nullable=False)

        batch_op.drop_constraint(
            "fk_karma_changes_message_id_messages", type_="foreignkey"
        )
        batch_op.drop_column("mid_old")

    # Drop if existing
    if "message_edits" in tables:
        op.drop_table("message_edits")
    if "messages" in tables:
        op.drop_table("messages")

    with op.batch_alter_table(
        "user_vote", schema=None, naming_convention=nc
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
        "user_vote", schema=None, naming_convention=nc
    ) as batch_op:
        batch_op.drop_constraint("fk_user_vote_vote_id_vote_choice", type_="foreignkey")

    op.create_table(
        "message_edits",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("original_message", sa.INTEGER(), nullable=False),
        sa.Column("new_content", sa.BLOB(), nullable=False),
        sa.Column("created_at", sa.DATETIME(), nullable=False),
        sa.ForeignKeyConstraint(
            ["original_message"],
            ["messages.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column("message_uid", sa.BIGINT(), nullable=False),
        sa.Column("message_content", sa.BLOB(), nullable=False),
        sa.Column("author", sa.INTEGER(), nullable=False),
        sa.Column("created_at", sa.DATETIME(), nullable=False),
        sa.Column("channel_name", sa.BLOB(), nullable=False),
        sa.Column("deleted_at", sa.DATETIME(), nullable=True),
        sa.ForeignKeyConstraint(
            ["author"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table(
        "karma_changes", schema=None, naming_convention=nc
    ) as batch_op:
        batch_op.add_column(sa.Column("mid_old", sa.INTEGER(), nullable=True))
        batch_op.create_foreign_key(
            "fk_karma_changes_message_id_messages", "messages", ["mid_old"], ["id"]
        )
        batch_op.alter_column("message_id", existing_type=sa.BIGINT(), nullable=True)
