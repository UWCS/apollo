import logging

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

from config import CONFIG

__all__ = ["Base", "db_session", "auto_str"]


Base = declarative_base()

engine = create_engine(CONFIG.DATABASE_CONNECTION)
if CONFIG.SQL_LOGGING:
    logging.basicConfig()
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
db_session = Session(bind=engine)


def auto_str(cls):
    def __str__(self):
        value = ", ".join("{}={}".format(*item) for item in vars(self).items())
        return f"{type(self).__name__}({value})"

    cls.__str__ = __str__
    return cls
