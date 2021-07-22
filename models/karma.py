from pytz import timezone, utc
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from models.models import Base, auto_str

__all__ = ["KarmaChange", "Karma", "BlockedKarma"]


@auto_str
class KarmaChange(Base):
    __tablename__ = "karma_changes"

    karma_id = Column(Integer, ForeignKey("karma.id"), primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True, nullable=False)
    message_id = Column(
        Integer, ForeignKey("messages.id"), primary_key=True, nullable=False
    )
    created_at = Column(DateTime, nullable=False)
    reason = Column(String(), nullable=True)
    change = Column(Integer, nullable=False)
    score = Column(Integer, nullable=False)

    karma = relationship("Karma", back_populates="changes")
    user = relationship("User", back_populates="karma_changes")
    message = relationship("LoggedMessage", back_populates="karma")

    @hybrid_property
    def local_time(self):
        return utc.localize(self.created_at).astimezone(timezone("Europe/London"))


@auto_str
class Karma(Base):
    __tablename__ = "karma"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    added = Column(
        DateTime,
        nullable=False,
        default=func.current_timestamp(),
    )
    pluses = Column(Integer, nullable=False, default=0)
    minuses = Column(Integer, nullable=False, default=0)
    neutrals = Column(Integer, nullable=False, default=0)

    changes = relationship(
        "KarmaChange", back_populates="karma", order_by=KarmaChange.created_at.asc()
    )

    @hybrid_property
    def net_score(self):
        return self.pluses - self.minuses

    @hybrid_property
    def total_karma(self):
        return self.pluses + self.minuses + self.neutrals


@auto_str
class BlockedKarma(Base):
    __tablename__ = "blacklist"

    topic = Column(String, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    added_at = Column(DateTime, nullable=False, default=func.current_timestamp())
