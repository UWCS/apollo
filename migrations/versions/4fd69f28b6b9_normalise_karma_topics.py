"""Normalise karma topics

Revision ID: 4fd69f28b6b9
Revises: f1e50ee892b4
Create Date: 2021-07-12 20:11:42.424516

"""
import unicodedata
from typing import Dict, List, Tuple

import sqlalchemy as sa
from alembic import op
from sqlalchemy import orm
from sqlalchemy.orm import declarative_base

# revision identifiers, used by Alembic.
revision = "4fd69f28b6b9"
down_revision = "f1e50ee892b4"
branch_labels = None
depends_on = None


Base = declarative_base()


# Models for finding foreign keys
class User(Base):
    __tablename__ = "users"
    id = sa.Column(sa.Integer, primary_key=True, nullable=False)


class Message(Base):
    __tablename__ = "messages"
    id = sa.Column(sa.Integer, primary_key=True, nullable=False)


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
    reason = sa.Column(sa.String(1024), nullable=True)

    karma = sa.orm.relationship("Karma", back_populates="changes")


class Karma(Base):
    __tablename__ = "karma"
    id = sa.Column(sa.Integer, primary_key=True, nullable=False)
    name = sa.Column(sa.String, nullable=False)
    added = sa.Column(
        sa.DateTime,
        nullable=False,
        default=sa.func.current_timestamp(),
    )
    pluses = sa.Column(sa.Integer, nullable=False, default=0)
    minuses = sa.Column(sa.Integer, nullable=False, default=0)
    neutrals = sa.Column(sa.Integer, nullable=False, default=0)

    changes = sa.orm.relationship(
        "KarmaChange", back_populates="karma", order_by=KarmaChange.created_at.asc()
    )


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)
    karma_items = session.query(Karma).order_by(Karma.added.asc())

    def topic_transformations(k: Karma):
        topic = k.name.casefold()
        yield topic
        yield topic.replace(" ", "_")
        yield topic.replace("_", " ")
        topic = unicodedata.normalize("NFKD", topic)
        yield topic
        yield topic.replace(" ", "_")
        yield topic.replace("_", " ")
        topic = "".join(c for c in topic if not unicodedata.combining(c))
        yield topic
        yield topic.replace(" ", "_")
        yield topic.replace("_", " ")

    karma_mapping: Dict[str, Tuple[Karma, List[Karma]]] = {}

    # karma_items is sorted by creation time (ascending) so older items go first.
    # This means when two karma items are being merged into one, the oldest will take precedence.
    karma: Karma
    for karma in karma_items:
        if (
            key := next(
                (t for t in topic_transformations(karma) if t in karma_mapping), None
            )
        ) is not None:
            # If we found any of the transformed versions of this item in the dictionary,
            # append this item to the relevant list.
            karma_mapping[key][1].append(karma)
        else:
            # Otherwise, we must have a new item so inset it into the dictionary with an empty list.
            karma_mapping[karma.name] = karma, []

    # Now we must update all of the karma_changes of the values in the dictionary to point at the de-duplicated
    # Karma entries.
    # At the same time, we have to re-calculate several columns on the existing items.
    for karma_item, duplicates in karma_mapping.values():
        for duplicate in duplicates:
            karma_item.pluses += duplicate.pluses
            karma_item.minuses += duplicate.minuses
            karma_item.neutrals += duplicate.neutrals
            for change in duplicate.changes:
                change.karma_id = karma_item.id
                change.karma = karma_item
            session.delete(duplicate)

    session.commit()
    session.close()


def downgrade():
    """Nothing we can do to downgrade - this is a one-way operation."""
    pass
