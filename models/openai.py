from sqlalchemy.orm import Mapped, mapped_column

from models.models import Base, UserId


class OpenAI(Base):
    __tablename__ = "openai"
    user_id: Mapped[UserId] = mapped_column(primary_key=True)
