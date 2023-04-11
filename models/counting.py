from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Mapped, mapped_column

from models.models import Base, IntPk, UserId


class CountingRun(Base):
    __tablename__ = "counting_runs"

    id: Mapped[IntPk] = mapped_column(init=False)
    started_at: Mapped[datetime]
    ended_at: Mapped[datetime]
    length: Mapped[int]
    step: Mapped[Decimal]


class CountingUser(Base):
    __tablename__ = "counting_users"
    id: Mapped[IntPk] = mapped_column(init=False)

    user_id: Mapped[UserId]
    correct_replies: Mapped[int]
    wrong_replies: Mapped[int]
