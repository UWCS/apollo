from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from models.models import Base, DiscordSnowflake, UserId


class IgnoredChannel(Base):
    __tablename__ = "ignored_channels"

    channel: Mapped[DiscordSnowflake] = mapped_column(primary_key=True)
    user_id: Mapped[UserId]
    added_at: Mapped[datetime] = mapped_column(
        default_factory=datetime.now, insert_default=func.current_timestamp()
    )


class MiniKarmaChannel(Base):
    __tablename__ = "mini_karma_channels"

    channel: Mapped[DiscordSnowflake] = mapped_column(primary_key=True)
    user_id: Mapped[UserId]
    added_at: Mapped[datetime] = mapped_column(
        default_factory=datetime.now, insert_default=func.current_timestamp()
    )
