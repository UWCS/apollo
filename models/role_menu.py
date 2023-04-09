from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.models import Base, discord_snowflake, int_pk


class RoleMenu(Base):
    __tablename__ = "rolemenu"
    id: Mapped[int_pk] = mapped_column(init=False)
    msg_ref: Mapped[str]
    guild_id: Mapped[discord_snowflake]
    channel_id: Mapped[discord_snowflake]
    choices: Mapped[list["RoleEntry"]] = relationship(
        "RoleEntry", back_populates="menu", cascade="all, delete-orphan", init=False
    )
    title: Mapped[str] = mapped_column(default="Vote", insert_default="Vote")
    message_id: Mapped[discord_snowflake | None] = mapped_column(default=None)
    unique_roles: Mapped[bool] = mapped_column(default=False)


class RoleEntry(Base):
    __tablename__ = "roleentry"
    menu_id: Mapped[int] = mapped_column(
        ForeignKey("rolemenu.id", ondelete="CASCADE"),
        primary_key=True,
    )
    menu: Mapped["RoleMenu"] = relationship(back_populates="choices", init=False)
    role: Mapped[discord_snowflake] = mapped_column(primary_key=True)
    title: Mapped[str]
    description: Mapped[str | None] = mapped_column(default=None)
    emoji: Mapped[str | None] = mapped_column(default=None)
