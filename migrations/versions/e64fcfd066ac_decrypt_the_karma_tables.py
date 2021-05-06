"""Decrypt the karma tables

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


# These models are defined so that SQLAlchemy can find the foreign keys
class User(Base):
    __tablename__ = "users"
    id = sa.Column(sa.Integer, primary_key=True, nullable=False)


class Message(Base):
    __tablename__ = "messages"
    id = sa.Column(sa.Integer, primary_key=True, nullable=False)


# These are the models we're actually changing
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
    reasons = sa.Column(
        sau.EncryptedType(type_in=sau.ScalarListType(str), key=secret_key),
        nullable=True,
    )
    reasons_new = sa.Column(sau.ScalarListType(str, separator=";"), nullable=True)


class Karma(Base):
    __tablename__ = "karma"

    id = sa.Column(sa.Integer, primary_key=True, nullable=False)
    name = sa.Column(sa.String, nullable=False)
    added = sa.Column(
        sau.EncryptedType(type_in=sa.DateTime, key=secret_key),
        nullable=False,
        default=sa.func.current_timestamp(),
    )
    added_new = sa.Column(
        sa.DateTime,
        nullable=False,
        default=sa.func.current_timestamp(),
    )
    pluses = sa.Column(sa.Integer, nullable=False, default=0)
    minuses = sa.Column(sa.Integer, nullable=False, default=0)
    neutrals = sa.Column(sa.Integer, nullable=False, default=0)


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    op.add_column(
        "karma_changes", sa.Column("reasons_new", sau.ScalarListType, nullable=True)
    )

    recreate = "always" if bind.engine.name == "sqlite" else "never"
    with op.batch_alter_table("karma", recreate=recreate) as bop:
        bop.add_column(
            sa.Column(
                "added_new",
                sa.DateTime,
                nullable=False,
                server_default=sa.func.current_timestamp(),
            ),
        )

    # Decrypt the reason and save it with the new separator
    for change in session.query(KarmaChange):
        change.reasons_new = change.reasons

    # Decrypt the added column
    for karma in session.query(Karma):
        karma.added_new = karma.added

    session.commit()

    with op.batch_alter_table("karma_changes") as bop:
        bop.drop_column("reasons")
        bop.alter_column("reasons_new", new_column_name="reasons")

    with op.batch_alter_table("karma") as bop:
        bop.drop_column("added")
        bop.alter_column("added_new", new_column_name="added")


def downgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    with op.batch_alter_table("karma_changes") as bop:
        bop.alter_column("reasons", new_column_name="reasons_new")

    with op.batch_alter_table("karma") as bop:
        bop.alter_column("added", new_column_name="added_new")

    # We have to start with nullable=True until the values are populated
    op.add_column(
        "karma_changes", sa.Column("reasons", sau.EncryptedType, nullable=True)
    )

    recreate = "always" if bind.engine.name == "sqlite" else "never"
    with op.batch_alter_table("karma", recreate=recreate) as bop:
        bop.add_column(
            sa.Column(
                "added",
                sau.EncryptedType,
                nullable=True,
                default=sa.func.current_timestamp(),
            ),
        )

    # Re-encrypt the reasons
    for change in session.query(KarmaChange):
        change.reasons = change.reasons_new

    # Re-encrypt the added
    for karma in session.query(Karma):
        karma.added = karma.added_new

    session.commit()

    with op.batch_alter_table("karma_changes") as bop:
        bop.drop_column("reasons_new")

    with op.batch_alter_table("karma") as bop:
        # Now we can mark the column as non-nullable
        bop.alter_column("added", nullable=False)
        bop.drop_column("added_new")
