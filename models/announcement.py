from sqlalchemy import func
from sqlalchemy.orm import relationship, mapped_column, Mapped
from datetime import datetime
from models.models import Base, user_id, int_pk
from models.user import User


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[int_pk]
    user_id: Mapped[user_id]

    announcement_content: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=func.current_timestamp())
    trigger_at: Mapped[datetime]
    triggered: Mapped[bool]
    playback_channel_id: Mapped[int]
    irc_name: Mapped[str | None]

    user: Mapped["User"] = relationship(
        "User",
        uselist=False,
    )
