from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import BigInteger, Boolean, Integer, String

from models.models import Base, auto_str

__all__ = ["RoleMenu", "RoleEntry"]


@auto_str
class RoleMenu(Base):
    __tablename__ = "rolemenu"
    id = Column(Integer, primary_key=True)
    msg_ref = Column(String, nullable=False)
    guild_id = Column(BigInteger, nullable=False)
    title = Column(String, nullable=False, server_default="Vote")
    channel_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger)
    unique_roles = Column(Boolean, default=False)

    choices = relationship(
        "RoleEntry", back_populates="menu", cascade="all, delete-orphan"
    )


@auto_str
class RoleEntry(Base):
    __tablename__ = "roleentry"
    menu_id = Column(
        Integer,
        ForeignKey("rolemenu.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    role = Column(BigInteger, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    emoji = Column(String)

    menu = relationship(RoleMenu, back_populates="choices")
