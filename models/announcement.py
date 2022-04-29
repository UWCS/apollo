from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from models.models import Base, auto_str

__all__ = ["Announcement"]


@auto_str
class Announcement(Base):
    __tablename__ = "announcements"
    id = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    announcement_content = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    trigger_at = Column(DateTime, nullable=False)
    triggered = Column(Boolean, nullable=False)
    playback_channel_id = Column(BigInteger, nullable=False)
    irc_name = Column(String, nullable=True)

    user = relationship(
        "User",
        uselist=False,
    )
