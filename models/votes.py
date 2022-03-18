import enum

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
    Enum,
    Boolean,
    ForeignKeyConstraint
)

from models.models import Base, auto_str


__all__ = ["VoteType", "Vote", "UserVote", "VoteChoice", "DiscordVoteChoice", "DiscordVoteMessage", "DiscordVote"]

class VoteType(enum.Enum):
    basic = 0
    fptp = 1
    approval = 2
    stv = 3
    ranked_pairs = 4


@auto_str
class Vote(Base):
    __tablename__ = "vote"
    id = Column(Integer, primary_key=True, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False, server_default="Vote")
    vote_limit = Column(Integer, nullable=False, server_default="0")
    ranked_choice = Column(Boolean, nullable=False)
    type = Column(Enum(VoteType), nullable=False)
    seats = Column(Integer, nullable=False, server_default="1")
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())

    # choices = relationship(
    #     "VoteChoice", backref="vote", order_by=VoteChoice.choice_index
    # )
    # votes = relationship("UserVote", backref="vote")


@auto_str
class UserVote(Base):
    __tablename__ = "user_vote"
    vote_id = Column(Integer, ForeignKey("vote.id"), primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True, nullable=False)
    choice = Column(
        Integer, ForeignKey("vote_choice.id"), primary_key=True, nullable=False
    )
    preference = Column(Integer, nullable=False, server_default="0")


@auto_str
class VoteChoice(Base):
    __tablename__ = "vote_choice"
    vote_id = Column(
        Integer,
        ForeignKey("vote.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    choice_index = Column(Integer, primary_key=True, nullable=False)
    choice = Column(String, nullable=False)


#
@auto_str
class DiscordVoteChoice(Base):
    __tablename__ = "discord_vote_choice"
    vote_id = Column(Integer, primary_key=True, nullable=False)
    choice_index = Column(Integer, primary_key=True, nullable=False)
    emoji = Column(String)
    msg = Column(Integer, ForeignKey("discord_vote_message"))
    # choice = relationship("VoteChoice")
    ForeignKeyConstraint((vote_id, choice_index), (VoteChoice.vote_id, VoteChoice.choice_index))


@auto_str
class DiscordVoteMessage(Base):
    __tablename__ = "discord_vote_message"
    message_id = Column(Integer, primary_key=True)
    channel_id = Column(Integer, nullable=False)
    vote_id = Column(Integer, ForeignKey("discord_vote.id"), ForeignKey("vote.id", ondelete="CASCADE"), nullable=False)
    choices_start_index = Column(Integer, nullable=False)
    numb_choices = Column(Integer, nullable=False, server_default="20")
    part = Column(Integer, nullable=False)

    # discord_vote = relationship("DiscordVote")
    # vote = relationship("Vote")
    # overlaps = "discord_vote"


# Currently pretty useless
@auto_str
class DiscordVote(Base):
    __tablename__ = "discord_vote"
    id = Column(Integer, ForeignKey("vote.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    allowed_role_id = Column(Integer)
    # messages = relationship("DiscordVoteMessage", backref="vote", order_by=DiscordVoteMessage.part)
    # vote = relationship("Vote")
