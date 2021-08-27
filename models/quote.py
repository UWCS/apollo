from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from models.models import Base, auto_str

__all__ = ["Quote"]


@auto_str
class Quote(Base):
    __tablename__ = "quotes"
    quote_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    submitter_type = Column(Enum("id", "string", name="submitter_type"), nullable=False)
    submitter_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    submitter_string = Column(String, nullable=True)
    author_type = Column(Enum("id", "string", name="author_type"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    author_string = Column(String, nullable=True)
    quote = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    edited = Column(Boolean, nullable=False)
    edited_at = Column(DateTime, nullable=True)

    author = relationship("User", uselist=False, foreign_keys=author_id)

    def author_to_string(self) -> str:
        if self.author_type == "id":
            return f"<@{self.author.user_uid}>"
        return self.author_string