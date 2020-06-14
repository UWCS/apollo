"""Decrypt the karma reasons list

Revision ID: e64fcfd066ac
Revises: eb0c99ae1f63
Create Date: 2020-05-02 14:44:07.337112

"""
import os

import sqlalchemy as sa
import sqlalchemy_utils as sau
from alembic import op
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base

# revision identifiers, used by Alembic.
revision = "e64fcfd066ac"
down_revision = "eb0c99ae1f63"
branch_labels = None
depends_on = None

Base = declarative_base()

if os.environ.get("SECRET_KEY") is None:
    raise EnvironmentError("Please define env var SECRET_KEY")
secret_key = os.environ.get("SECRET_KEY")


class KarmaChange(Base):
    __tablename__ = "karma_changes"

    karma_id = sa.Column(
        sa.Integer, sa.ForeignKey("karma.id"), primary_key=True, nullable=False
    )
    user_id = sa.Column(
        sa.Integer, sa.ForeignKey("users.id"), primary_key=True, nullable=False
    )
    message_id = sa.Column(
        sa.Integer, sa.ForeignKey("messages.id"), primary_key=True, nullable=False
    )
    created_at = sa.Column(sa.DateTime, nullable=False)
    # Using a Greek question mark (;) instead of a semicolon here!
    reasons = sa.Column(
        sau.EncryptedType(type_in=sau.ScalarListType(str), key=secret_key),
        nullable=True,
    )
    reasons_new = sa.Column(sau.ScalarListType(str, separator=";"), nullable=True)


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    op.add_column(
        "karma_changes", sa.Column("reasons_new", sau.ScalarListType, nullable=True)
    )

    # Decrypt the reason and save it with the new separator
    for change in session.query(KarmaChange):
        change.reasons_new = change.reasons

    op.drop_column("karma_changes", "reasons")
    with op.batch_alter_table("karma_changes") as bop:
        bop.alter_column("reasons_new", new_column_name="reasons")


def downgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    with op.batch_alter_table("karma_changes") as bop:
        bop.alter_column("reasons", new_column_name="reasons_new")

    op.add_column(
        "karma_changes", sa.Column("reasons", sau.EncryptedType, nullable=True)
    )

    # Re-encrypt the reasons
    for change in session.query(KarmaChange):
        change.reasons = change.reasons_new

    op.drop_column("karma_changes", "reasons_new")
