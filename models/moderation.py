import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from models.models import Base, auto_str


@enum.unique
class ModerationAction(enum.Enum):
    """Which moderation action a particular row represents.

    Values are specified to ensure they always match up with the database.
    SQLAlchemy usually uses a string of the name as the database-side representation
    but just in case it doesn't at some point they're explicitly defined.
    """

    TEMPMUTE = 0
    MUTE = 1
    UNMUTE = 2
    WARN = 3
    REMOVE_WARN = 4
    AUTOWARN = 5
    REMOVE_AUTOWARN = 6
    AUTOMUTE = 7
    REMOVE_AUTOMUTE = 8
    KICK = 9
    TEMPBAN = 10
    BAN = 11
    UNBAN = 12


@auto_str
class ModerationHistory(Base):
    __tablename__ = "moderation_history"

    id = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=func.current_timestamp())
    action = Column(Enum(ModerationAction), nullable=False)
    reason = Column(String, nullable=True)
    moderator_id = Column(Integer, ForeignKey("users.id"), nullable=False)


@auto_str
class ModerationTemporaryActions(Base):
    __tablename__ = "moderation_temporary_actions"

    moderation_item_id = Column(
        Integer, ForeignKey("moderation_history.id"), primary_key=True, nullable=False
    )
    until = Column(DateTime, nullable=False)
    complete = Column(Boolean, nullable=False)

    main_item = relationship("ModerationHistory", uselist=False)


@auto_str
class ModerationLinkedItems(Base):
    __tablename__ = "moderation_linked_items"

    moderation_item_id = Column(
        Integer, ForeignKey("moderation_history.id"), primary_key=True, nullable=False
    )
    linked_item = Column(Integer, ForeignKey("moderation_history.id"), nullable=False)

    main_item = relationship(
        "ModerationHistory", uselist=False, foreign_keys=[moderation_item_id]
    )
