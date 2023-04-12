from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.karma import KarmaChange
from models.models import Base, DiscordSnowflake


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    user_uid: Mapped[DiscordSnowflake]
    username: Mapped[str]
    karma_changes: Mapped[list["KarmaChange"]] = relationship(
        back_populates="user", order_by=KarmaChange.created_at, init=False
    )
