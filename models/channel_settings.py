from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, func

from models.models import Base, auto_str

__all__ = ["IgnoredChannel", "MiniKarmaChannel"]


@auto_str
class IgnoredChannel(Base):
    __tablename__ = "ignored_channels"

    channel = Column(BigInteger, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    added_at = Column(DateTime, nullable=False, default=func.current_timestamp())


@auto_str
class MiniKarmaChannel(Base):
    __tablename__ = "mini_karma_channels"

    channel = Column(BigInteger, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    added_at = Column(DateTime, nullable=False, default=func.current_timestamp())
