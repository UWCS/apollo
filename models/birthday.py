from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from models.models import Base, IntPk


class Birthday(Base):
    __tablename__ = "birthdays"
    id: Mapped[IntPk] = mapped_column(init=False)
    date: Mapped[datetime]
    age: Mapped[int]
