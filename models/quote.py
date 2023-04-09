from sqlalchemy import func
from sqlalchemy.orm import relationship, mapped_column, Mapped

from models.models import Base, user_id
from utils.mentions import MentionType
from datetime import datetime
from models.user import User


class Quote(Base):
    __tablename__ = "quotes"
    quote_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    author_type: Mapped[MentionType]
    author_id: Mapped[user_id | None]
    author_string: Mapped[str | None]

    quote: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=func.current_timestamp())
    edited_at: Mapped[datetime | None]

    author: Mapped["User"] = relationship("User", uselist=False, foreign_keys=author_id)  # type: ignore # there is probably a better way to do this

    def author_to_string(self) -> str:
        match self.author_type:
            case MentionType.ID:
                return f"<@{self.author.user_uid}>"
            case MentionType.STRING:
                assert self.author_string
                return self.author_string

    @staticmethod
    def id_quote(id: int, quote: str, created: datetime):
        return Quote(
            author_type=MentionType.ID, author_id=id, quote=quote, created_at=created
        )

    @staticmethod
    def string_quote(string: str, quote: str, created: datetime):
        return Quote(
            author_type=MentionType.STRING,
            author_string=string,
            quote=quote,
            created_at=created,
        )


class QuoteOptouts(Base):
    __tablename__ = "quotes_opt_out"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_type: Mapped[MentionType]
    user_id: Mapped[user_id]
    user_string: Mapped[str]
