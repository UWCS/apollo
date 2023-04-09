from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column

from models.models import Base, discord_snowflake, int_pk, discord_snowflake_pk


class RoleMenu(Base):
    __tablename__ = "rolemenu"
    id: Mapped[int_pk]
    msg_ref: Mapped[str]
    guild_id: Mapped[discord_snowflake]
    title: Mapped[str] = mapped_column(server_default="Vote")
    channel_id: Mapped[discord_snowflake]
    message_id: Mapped[discord_snowflake | None]
    unique_roles: Mapped[bool] = mapped_column(default=False)

    choices: Mapped[list["RoleEntry"]] = relationship(
        "RoleEntry", back_populates="menu", cascade="all, delete-orphan"
    )


class RoleEntry(Base):
    __tablename__ = "roleentry"
    menu_id: Mapped[int] = mapped_column(
        ForeignKey("rolemenu.id", ondelete="CASCADE"),
        primary_key=True,
    )

    role: Mapped[discord_snowflake_pk]
    title: Mapped[str]
    description: Mapped[str | None]
    emoji: Mapped[str | None]

    menu: Mapped["RoleMenu"] = relationship(back_populates="choices")
