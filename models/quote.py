from datetime import datetime

from sqlalchemy import func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.models import Base, user_id
from models.user import User
from utils.mentions import MentionType
from typing import Optional


class Quote(Base):
    __tablename__ = "quotes"
    quote_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, init=False
    )
    author_type: Mapped[MentionType]
    quote: Mapped[str]
    author_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    author: Mapped[Optional["User"]] = relationship(
        "User", uselist=False, foreign_keys=author_id, init=False
    )
    author_string: Mapped[Optional[str]] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(
        default_factory=datetime.now, insert_default=func.current_timestamp()
    )
    edited_at: Mapped[Optional[datetime]] = mapped_column(default=None)

    def author_to_string(self) -> str:
        match self.author_type:
            case MentionType.ID:
                assert self.author
                return f"<@{self.author.user_uid}>"
            case MentionType.STRING:
                assert self.author_string
                return self.author_string

    @staticmethod
    def id_quote(id: int, quote: str, created: datetime):
        return Quote(
            author_type=MentionType.ID,
            author_id=id,
            quote=quote,
            created_at=created,
        )

    @staticmethod
    def string_quote(string: str, quote: str, created: datetime):
        return Quote(
            author_type=MentionType.STRING,
            author_string=string,
            quote=quote,
            created_at=created,
            author_id=None,
        )


class QuoteOptouts(Base):
    __tablename__ = "quotes_opt_out"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    user_type: Mapped[MentionType]
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    user_string: Mapped[Optional[str]]
