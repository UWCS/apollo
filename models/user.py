from sqlalchemy import BigInteger, Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship
from sqlalchemy_utils import EncryptedType

from config import CONFIG
from models import KarmaChange, LoggedMessage
from models.models import Base, auto_str

__all__ = ["User"]


@auto_str
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, nullable=False)
    user_uid = Column(BigInteger, nullable=False)
    username = Column(
        EncryptedType(type_in=String, key=CONFIG.BOT_SECRET_KEY), nullable=False
    )
    first_seen = Column(DateTime, nullable=False, default=func.current_timestamp())
    last_seen = Column(DateTime, nullable=False, default=func.current_timestamp())
    uni_id = Column(
        EncryptedType(type_in=String, key=CONFIG.BOT_SECRET_KEY), nullable=True
    )
    verified_at = Column(
        EncryptedType(type_in=DateTime, key=CONFIG.BOT_SECRET_KEY), nullable=True
    )

    messages = relationship(
        "LoggedMessage", back_populates="user", order_by=LoggedMessage.created_at
    )
    karma_changes = relationship(
        "KarmaChange", back_populates="user", order_by=KarmaChange.created_at
    )
