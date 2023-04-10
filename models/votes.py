import enum
from datetime import datetime

from sqlalchemy import ForeignKey, ForeignKeyConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.models import Base, DiscordSnowflake, UserId, IntPk
from models.user import User


class VoteType(enum.Enum):
    basic = 0
    fptp = 1
    approval = 2
    stv = 3
    ranked_pairs = 4


class Vote(Base):
    __tablename__ = "vote"
    id: Mapped[IntPk] = mapped_column(primary_key=True, init=False)
    owner_id: Mapped[UserId]
    type: Mapped[VoteType]
    ranked_choice: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(
        default_factory=datetime.now, insert_default=func.current_timestamp()
    )
    title: Mapped[str] = mapped_column(default="Vote")
    vote_limit: Mapped[int] = mapped_column(default="0")
    seats: Mapped[int] = mapped_column(default="1")

    choices: Mapped[list["VoteChoice"]] = relationship(
        back_populates="vote", cascade="all, delete-orphan", init=False
    )
    discord_vote: Mapped[list["DiscordVote"]] = relationship(
        back_populates="vote", cascade="all, delete-orphan", init=False
    )


class VoteChoice(Base):
    __tablename__ = "vote_choice"
    vote_id: Mapped[int] = mapped_column(
        ForeignKey("vote.id", ondelete="CASCADE"), primary_key=True
    )
    vote: Mapped[Vote] = relationship(back_populates="choices", init=False)
    choice_index: Mapped[int] = mapped_column(primary_key=True)
    choice: Mapped[str]

    user_votes: Mapped[list["UserVote"]] = relationship(
        back_populates="vote_choice", cascade="all, delete-orphan", init=False
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
        back_populates="user_votes", init=False
    )
    preference: Mapped[int] = mapped_column(server_default="0", init=False)
    ForeignKeyConstraint(
        (vote_id, choice),
        (VoteChoice.vote_id, VoteChoice.choice_index),
        ondelete="CASCADE",
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
    numb_choices: Mapped[int] = mapped_column(server_default="20", init=False)
    part: Mapped[int]

    discord_vote: Mapped["DiscordVote"] = relationship(
        back_populates="messages", init=False
    )


# TODO Add unique constraints, remove emoji
class DiscordVoteChoice(Base):
    __tablename__ = "discord_vote_choice"
    vote_id: Mapped[int] = mapped_column(primary_key=True)
    choice_index: Mapped[int] = mapped_column(primary_key=True)
    msg_id: Mapped[int] = mapped_column(
        ForeignKey("discord_vote_message.message_id", ondelete="CASCADE")
    )
    msg: Mapped["DiscordVoteMessage"]
    emoji: Mapped[str | None] = mapped_column(default="", init=False)
    __table_args__ = (
        ForeignKeyConstraint(
            (vote_id, choice_index), (VoteChoice.vote_id, VoteChoice.choice_index)
        ),
    )
    choice: Mapped[VoteChoice] = relationship(init=False)


# Currently pretty useless
# TODO Limit to role
class DiscordVote(Base):
    __tablename__ = "discord_vote"
    id: Mapped[int] = mapped_column(
        ForeignKey("vote.id", ondelete="CASCADE"),
        primary_key=True,
    )
    vote: Mapped[Vote] = mapped_column(back_populates="discord_vote")
    allowed_role_id: Mapped[int]

    messages: Mapped["DiscordVoteMessage"] = mapped_column(
        back_populates="discord_vote", cascade="all, delete-orphan"
    )
