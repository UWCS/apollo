import logging

from sqlalchemy import create_engine, ForeignKey, BigInteger
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass, Session, mapped_column
from typing_extensions import Annotated
from config import CONFIG

# this is bad, redo this
engine = create_engine(CONFIG.DATABASE_CONNECTION, future=True)
if CONFIG.SQL_LOGGING:
    logging.basicConfig()
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
db_session = Session(bind=engine, future=True)


# also to be deprecated in favour of new dataclass functionality
def auto_str(cls):
    def __repr__(self):
        value = ", ".join(
            "{}={}".format(*item)
            for item in vars(self).items()
            if item[0] != "_sa_instance_state"
        )
        return f"{type(self).__name__} {{{value}}}"

    cls.__repr__ = __repr__
    return cls


int_pk = Annotated[int, mapped_column(primary_key=True)]
user_id = Annotated[int, mapped_column(ForeignKey("users.id"), nullable=False)]

# discord 'snowflakes' are the really long IDs that you get as like channel or user IDs
# this annotated column map type uses BigInteger to encode those and convert to python ints
discord_snowflake = Annotated[int, mapped_column(BigInteger, nullable=False)]
discord_snowflake_pk = Annotated[int, mapped_column(BigInteger, primary_key=True)]


class Base(DeclarativeBase):
    """
    Base model for all of Apollo's Models
    Uses SQLAlchemy's declarative dataclass mapping API
    """
