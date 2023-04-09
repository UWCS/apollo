from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Mapped

from models.models import Base, int_pk, user_id


class CountingRun(Base):
    __tablename__ = "counting_runs"

    id: Mapped[int_pk]
    started_at: Mapped[datetime]
    ended_at: Mapped[datetime]
    length: Mapped[int]
    step: Mapped[Decimal]


class CountingUser(Base):
    __tablename__ = "counting_users"
    id: Mapped[int_pk]

    user_id: Mapped[user_id]
    correct_replies: Mapped[int]
    wrong_replies: Mapped[int]
