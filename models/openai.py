from sqlalchemy.orm import Mapped, mapped_column

from models.models import Base, UserId


class OpenAIBans(Base):
    __tablename__ = "openai_bans"
    user_id: Mapped[UserId] = mapped_column(primary_key=True)
