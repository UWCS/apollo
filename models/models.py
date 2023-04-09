import logging

from sqlalchemy import BigInteger, ForeignKey, create_engine
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, Session, mapped_column
from typing_extensions import Annotated
from config import CONFIG

# this is bad, redo this
engine = create_engine(CONFIG.DATABASE_CONNECTION, future=True)
if CONFIG.SQL_LOGGING:
    logging.basicConfig()
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
db_session = Session(bind=engine, future=True)

# some useful re-usable column types
int_pk = Annotated[int, mapped_column(primary_key=True, init=False)]
user_id = Annotated[int, mapped_column(ForeignKey("users.id"), nullable=False)]
# discord 'snowflakes' are the really long IDs that you get as like channel or user IDs
# this annotated column map type uses BigInteger to encode those and convert to python ints
discord_snowflake = Annotated[int, mapped_column(BigInteger, nullable=False)]


class Base(MappedAsDataclass, DeclarativeBase):
    """
    Base model for all of Apollo's Models
    Uses SQLAlchemy's declarative dataclass mapping API
    """
