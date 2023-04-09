from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.models import Base, discord_snowflake, int_pk, user_id
from models.user import User


class Reminder(Base):
    __tablename__ = "reminders"
    id: Mapped[int_pk]
    user_id: Mapped[user_id]
    reminder_content: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=func.current_timestamp())
    trigger_at: Mapped[datetime]
    triggered: Mapped[bool]
    playback_channel_id: Mapped[discord_snowflake]
    irc_name: Mapped[str | None]

    user: Mapped["User"] = relationship(
        "User",
        uselist=False,
    )
