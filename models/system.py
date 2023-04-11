from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import func
from models.models import Base, int_pk, discord_snowflake
from enum import Enum, unique


# only tracks events triggered by the user currently
@unique
class EventKind(Enum):
    RESTART = 0
    UPDATE = 1


class SystemEvent(Base):
    __tablename__ = "system_events"
    id: Mapped[int_pk] = mapped_column(init=False)

    kind: Mapped[EventKind]

    message_id: Mapped[discord_snowflake]  # id of message that triggered the event
    channel_id: Mapped[discord_snowflake]  # channel message is in

    acknowledged: Mapped[bool] = mapped_column(default=False, insert_default=False)
    time: Mapped[datetime] = mapped_column(
        default_factory=datetime.now, insert_default=func.current_timestamp()
    )
