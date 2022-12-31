"""Replace karma_change reasons with reason

Revision ID: f1e50ee892b4
Revises: e377bd474696
Create Date: 2021-03-06 22:05:31.664509

"""
import os

import sqlalchemy as sa
import sqlalchemy_utils as sau
from alembic import op
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base

from config.config import CONFIG

# revision identifiers, used by Alembic.

revision = "f1e50ee892b4"
down_revision = "e377bd474696"
branch_labels = None
depends_on = None

Base = declarative_base()

secret_key = CONFIG.BOT_SECRET_KEY
if secret_key is None:
    raise Exception("Set a secret key in config.yaml")


# Models for finding foreign keys
class Karma(Base):
    __tablename__ = "karma"
    id = sa.Column(sa.Integer, primary_key=True, nullable=False)


class User(Base):
    __tablename__ = "users"
    id = sa.Column(sa.Integer, primary_key=True, nullable=False)


class Message(Base):
    __tablename__ = "messages"
    id = sa.Column(sa.Integer, primary_key=True, nullable=False)


# Model that's being migrated
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
    reason = sa.Column(sa.String(1024), nullable=True)


def upgrade():
    bind = op.get_bind()
    session = orm.create_session(bind)

    op.add_column("karma_changes", sa.Column("reason", sa.String(), nullable=True))

    session.query(KarmaChange).update({"reason": KarmaChange.reasons})

    with op.batch_alter_table("karma_changes") as bop:
        bop.drop_column("reasons")


def downgrade():
    bind = op.get_bind()
    session = orm.create_session(bind)

    op.add_column(
        "karma_changes", sa.Column("reasons", sau.ScalarListType, nullable=True)
    )

    session.query(KarmaChange).update({"reasons": KarmaChange.reason})

    with op.batch_alter_table("karma_changes") as bop:
        bop.drop_column("reason")
