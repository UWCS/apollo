from sqlalchemy import (
    Column,
    Enum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from models.models import Base, auto_str

__all__ = ["QuoteOptouts"]

@auto_str
class QuoteOptouts(Base):
    __tablename__ ="quotes-opt-out"
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    user_type = Column(Enum("id", "string", name="user_type"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_string = Column(String, nullable=True)
