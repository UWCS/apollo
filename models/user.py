from sqlalchemy import String, func, DateTime
from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy_utils import EncryptedType  # type: ignore
from config import CONFIG
from models.karma import KarmaChange
from models.models import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_uid: Mapped[int]
    username: Mapped[str] = mapped_column(
        EncryptedType(type_in=String, key=CONFIG.BOT_SECRET_KEY)
    )
    first_seen: Mapped[datetime] = mapped_column(default=func.current_timestamp())
    last_seen: Mapped[datetime] = mapped_column(default=func.current_timestamp())

    uni_id = mapped_column(
        EncryptedType(type_in=String, key=CONFIG.BOT_SECRET_KEY), nullable=True
    )
    verified_at = mapped_column(
        EncryptedType(type_in=DateTime, key=CONFIG.BOT_SECRET_KEY), nullable=True
    )

    karma_changes: Mapped[list["KarmaChange"]] = relationship(
        back_populates="user", order_by=KarmaChange.created_at
    )
