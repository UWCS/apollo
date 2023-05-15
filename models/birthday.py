from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from models.models import Base, UserId


class Birthday(Base):
    __tablename__ = "birthdays"
    date: Mapped[datetime] = mapped_column(primary_key=True)
    age: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[UserId]
