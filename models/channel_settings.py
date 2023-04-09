from sqlalchemy import func
from sqlalchemy.orm import mapped_column, Mapped
from models.models import Base, user_id, int_pk, discord_snowflake_pk
from datetime import datetime


class IgnoredChannel(Base):
    __tablename__ = "ignored_channels"

    channel: Mapped[discord_snowflake_pk]
    user_id: Mapped[user_id]
    added_at: Mapped[datetime] = mapped_column(default=func.current_timestamp())


class MiniKarmaChannel(Base):
    __tablename__ = "mini_karma_channels"

    channel: Mapped[discord_snowflake_pk]
    user_id: Mapped[user_id]
    added_at: Mapped[datetime] = mapped_column(default=func.current_timestamp())
