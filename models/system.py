from datetime import datetime
from enum import Enum, unique

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from models.models import Base, DiscordSnowflake, IntPk


# only tracks events triggered by the user currently
@unique
class EventKind(Enum):
    RESTART = 0
    UPDATE = 1


class SystemEvent(Base):
    __tablename__ = "system_events"
    id: Mapped[IntPk] = mapped_column(init=False)

    kind: Mapped[EventKind]

    message_id: Mapped[DiscordSnowflake]  # id of message that triggered the event
    channel_id: Mapped[DiscordSnowflake]  # channel message is in

    acknowledged: Mapped[bool] = mapped_column(default=False, insert_default=False)
    time: Mapped[datetime] = mapped_column(
        default_factory=datetime.now, insert_default=func.current_timestamp()
    )
