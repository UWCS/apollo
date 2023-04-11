# pyright: reportImportCycles=false
# we need to import User for type checking but that gives a circular import

from datetime import datetime
from typing import TYPE_CHECKING

from pytz import timezone, utc
from sqlalchemy import ForeignKey, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.models import Base, DiscordSnowflake

# breaks the circular import at runtime
# still happens when type checking
if TYPE_CHECKING:
    from .user import User


class KarmaChange(Base):
    __tablename__ = "karma_changes"

    karma_id: Mapped[int] = mapped_column(ForeignKey("karma.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    message_id: Mapped[DiscordSnowflake] = mapped_column(primary_key=True)

    created_at: Mapped[datetime]
    reason: Mapped[str | None]
    change: Mapped[int]
    score: Mapped[int]

    karma: Mapped["Karma"] = relationship(back_populates="changes", init=False)
    user: Mapped["User"] = relationship(back_populates="karma_changes", init=False)

    @hybrid_property
    def local_time(self):
        return utc.localize(self.created_at).astimezone(timezone("Europe/London"))


class Karma(Base):
    __tablename__ = "karma"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    name: Mapped[str]

    changes: Mapped[list["KarmaChange"]] = relationship(
        back_populates="karma", order_by=KarmaChange.created_at.asc(), init=False
    )

    added: Mapped[datetime] = mapped_column(
        default=func.current_timestamp(),
    )
    pluses: Mapped[int] = mapped_column(default=0)
    minuses: Mapped[int] = mapped_column(default=0)
    neutrals: Mapped[int] = mapped_column(default=0)

    @hybrid_property
    def net_score(self):
        return self.pluses - self.minuses

    @hybrid_property
    def total_karma(self):
        return self.pluses + self.minuses + self.neutrals


class BlockedKarma(Base):
    __tablename__ = "blacklist"

    topic: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    added_at: Mapped[datetime] = mapped_column(default=func.current_timestamp())
