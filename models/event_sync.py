from sqlalchemy import BigInteger, Column, DateTime, String

from models.models import Base, auto_str

__all__ = ["EventLink"]


@auto_str
class EventLink(Base):
    __tablename__ = "event_links"
    uid = Column(String, primary_key=True)
    discord_event = Column(BigInteger, nullable=False, unique=True)
    last_modified = Column(DateTime)
