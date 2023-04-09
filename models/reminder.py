from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.models import Base, discord_snowflake, int_pk, user_id
from models.user import User


class Reminder(Base):
    __tablename__ = "reminders"
    id: Mapped[int_pk] = mapped_column(init=False)
    user_id: Mapped[user_id]
    reminder_content: Mapped[str]
    trigger_at: Mapped[datetime]
    triggered: Mapped[bool]
    playback_channel_id: Mapped[discord_snowflake]
    user: Mapped["User"] = relationship(
        "User",
        uselist=False,
    )
    irc_name: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(
       default_factory=datetime.now, insert_default=func.current_timestamp()
    )
