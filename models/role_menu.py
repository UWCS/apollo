from typing import Optional

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.models import Base, DiscordSnowflake, IntPk


class RoleMenu(Base):
    __tablename__ = "rolemenu"
    __table_args__ = (UniqueConstraint("msg_ref", "guild_id"),)

    id: Mapped[IntPk] = mapped_column(init=False)

    msg_ref: Mapped[str]
    guild_id: Mapped[DiscordSnowflake]
    channel_id: Mapped[DiscordSnowflake]
    choices: Mapped[list["RoleEntry"]] = relationship(
        "RoleEntry", back_populates="menu", cascade="all, delete-orphan", init=False
    )
    title: Mapped[str] = mapped_column(default="Vote", insert_default="Vote")

    message_id: Mapped[Optional[DiscordSnowflake]] = mapped_column(default=None)
    unique_roles: Mapped[Optional[bool]] = mapped_column(default=False)


class RoleEntry(Base):
    __tablename__ = "roleentry"
    menu_id: Mapped[int] = mapped_column(
        ForeignKey("rolemenu.id", ondelete="CASCADE"),
        primary_key=True,
    )
    menu: Mapped["RoleMenu"] = relationship(back_populates="choices", init=False)
    role: Mapped[DiscordSnowflake] = mapped_column(primary_key=True)
    title: Mapped[str]
    description: Mapped[Optional[str]] = mapped_column(default=None)
    emoji: Mapped[Optional[str]] = mapped_column(default=None)
