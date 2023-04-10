from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column

from models.models import Base, discord_snowflake


class EventLink(Base):
    __tablename__ = "event_links"
    uid: Mapped[str] = mapped_column(primary_key=True)
    discord_event: Mapped[discord_snowflake] = mapped_column(unique=True)
    last_modified: Mapped[Optional[datetime]]
