from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from models.models import Base, auto_str
from utils.mentions import MentionType

__all__ = ["Quote", "QuoteOptouts"]


@auto_str
class Quote(Base):
    __tablename__ = "quotes"
    quote_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    author_type = Column(Enum(MentionType), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    author_string = Column(String, nullable=True)
    quote = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    edited_at = Column(DateTime, nullable=True)

    author = relationship("User", uselist=False, foreign_keys=author_id)

    def author_to_string(self) -> str:
        if self.author_type == MentionType.ID:
            return f"<@{self.author.user_uid}>"
        return self.author_string

    @staticmethod
    def id_quote(id, quote, created):
        return Quote(
            author_type=MentionType.ID, author_id=id, quote=quote, created_at=created
        )

    @staticmethod
    def string_quote(string, quote, created):
        return Quote(
            author_type=MentionType.STRING,
            author_string=string,
            quote=quote,
            created_at=created,
        )


@auto_str
class QuoteOptouts(Base):
    __tablename__ = "quotes_opt_out"
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    user_type = Column(Enum(MentionType), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_string = Column(String, nullable=True)
