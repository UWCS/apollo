from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy_utils import EncryptedType

from config import CONFIG
from models.models import Base, auto_str

__all__ = ["MessageDiff", "LoggedMessage"]


@auto_str
class MessageDiff(Base):
    __tablename__ = "message_edits"

    id = Column(Integer, primary_key=True, nullable=False)
    original_message = Column(Integer, ForeignKey("messages.id"), nullable=False)
    new_content = Column(
        EncryptedType(type_in=String, key=CONFIG.BOT_SECRET_KEY), nullable=False
    )
    created_at = Column(DateTime, nullable=False)

    original = relationship("LoggedMessage", back_populates="edits")


@auto_str
class LoggedMessage(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, nullable=False)
    message_uid = Column(BigInteger, nullable=False)
    message_content = Column(
        EncryptedType(type_in=String, key=CONFIG.BOT_SECRET_KEY), nullable=False
    )
    author = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    channel_name = Column(
        EncryptedType(type_in=String, key=CONFIG.BOT_SECRET_KEY), nullable=False
    )

    user = relationship("User", back_populates="messages")
    edits = relationship(
        "MessageDiff", back_populates="original", order_by=MessageDiff.created_at
    )
    karma = relationship("KarmaChange", back_populates="message")
