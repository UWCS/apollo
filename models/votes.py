import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, ForeignKeyConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.models import Base, DiscordSnowflake, IntPk, UserId
from models.user import User


class VoteType(enum.Enum):
    basic = 0
    fptp = 1
    approval = 2
    stv = 3
    ranked_pairs = 4


class Vote(Base):
    __tablename__ = "vote"
    id: Mapped[IntPk] = mapped_column(init=False)
    owner_id: Mapped[UserId]
    type: Mapped[VoteType]
    ranked_choice: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(
        default_factory=datetime.now, insert_default=func.current_timestamp()
    )
    title: Mapped[str] = mapped_column(default="Vote")
    vote_limit: Mapped[int] = mapped_column(default=0)
    seats: Mapped[int] = mapped_column(default=1)

    choices: Mapped[list["VoteChoice"]] = relationship(
        init=False, cascade="all, delete-orphan", back_populates="vote"
    )
    discord_vote: Mapped["DiscordVote"] = relationship(
        init=False, cascade="all, delete-orphan", back_populates="vote"
    )


class VoteChoice(Base):
    __tablename__ = "vote_choice"
    vote_id: Mapped[int] = mapped_column(
        ForeignKey("vote.id", ondelete="CASCADE"), primary_key=True
    )
    vote: Mapped[Vote] = relationship(init=False, back_populates="choices")
    choice_index: Mapped[int] = mapped_column(primary_key=True)
    choice: Mapped[str]

    user_votes: Mapped[list["UserVote"]] = relationship(
        cascade="all, delete-orphan", init=False, back_populates="vote_choice"
    )


class UserVote(Base):
    __tablename__ = "user_vote"
    vote_id: Mapped[int] = mapped_column(
        ForeignKey(Vote.id, ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id), primary_key=True)
    user: Mapped[User] = relationship(init=False)
    choice: Mapped[int] = mapped_column(primary_key=True)
    vote_choice: Mapped[VoteChoice] = relationship(
        init=False, back_populates="user_votes"
    )
    preference: Mapped[int] = mapped_column(default=0, init=False)
    ForeignKeyConstraint(
        (vote_id, choice),
        (VoteChoice.vote_id, VoteChoice.choice_index),
        ondelete="CASCADE",
    )


# Currently pretty useless
# TODO Limit to role
class DiscordVote(Base):
    __tablename__ = "discord_vote"
    id: Mapped[int] = mapped_column(
        ForeignKey(Vote.id, ondelete="CASCADE"),
        primary_key=True,
    )
    vote: Mapped["Vote"] = relationship(init=False, back_populates="discord_vote")
    allowed_role_id: Mapped[Optional[int]] = mapped_column(default=None)

    messages: Mapped[list["DiscordVoteMessage"]] = relationship(
        init=False, cascade="all, delete-orphan"
    )


class DiscordVoteMessage(Base):
    __tablename__ = "discord_vote_message"
    message_id: Mapped[DiscordSnowflake] = mapped_column(primary_key=True)
    channel_id: Mapped[DiscordSnowflake]
    vote_id: Mapped[int] = mapped_column(
        ForeignKey("discord_vote.id", ondelete="CASCADE"),
        ForeignKey("vote.id", ondelete="CASCADE"),
    )
    choices_start_index: Mapped[int]
    part: Mapped[int]
    numb_choices: Mapped[int] = mapped_column(default=20)

    discord_vote: Mapped["DiscordVote"] = relationship(
        init=False, back_populates="messages"
    )


# # TODO Add unique constraints, remove emoji
class DiscordVoteChoice(Base):
    __tablename__ = "discord_vote_choice"
    vote_id: Mapped[int] = mapped_column(primary_key=True, init=False)
    choice_index: Mapped[int] = mapped_column(primary_key=True, init=False)
    msg_id: Mapped[DiscordSnowflake] = mapped_column(
        ForeignKey(DiscordVoteMessage.message_id, ondelete="CASCADE")
    )
    msg: Mapped[DiscordVoteMessage] = relationship(init=False)
    choice: Mapped[VoteChoice] = relationship()
    emoji: Mapped[Optional[str]] = mapped_column(default="")
    __table_args__ = (
        ForeignKeyConstraint(
            (vote_id, choice_index), (VoteChoice.vote_id, VoteChoice.choice_index)
        ),
    )
