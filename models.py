from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def auto_str(cls):
    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )

    cls.__str__ = __str__
    return cls


@auto_str
class User(Base):
    __tablename__ = 'users'
    # TODO: Add columns for ban counts/kick counts?
    id = Column(Integer, primary_key=True, nullable=False)
    user_uid = Column(String(length=250), nullable=False)
    username = Column(String(length=50), nullable=False)
    first_seen = Column(DateTime, nullable=False, default=datetime.now())
    last_seen = Column(DateTime, nullable=False, default=datetime.now())
    uni_id = Column(String(length=20), nullable=True)
