from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric

from models.models import Base, auto_str

__all__ = ["CountingRun", "CountingUser"]


@auto_str
class CountingRun(Base):
    __tablename__ = "counting_runs"
    id = Column(Integer, primary_key=True, nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=False)
    length = Column(Integer, nullable=False)
    step = Column(Numeric, nullable=False)


@auto_str
class CountingUser(Base):
    __tablename__ = "counting_users"
    id = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    correct_replies = Column(Integer, nullable=False)
    wrong_replies = Column(Integer, nullable=False)
