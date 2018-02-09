from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

from config import CONFIG

Base = declarative_base()

engine = create_engine(CONFIG['DATABASE_CONNECTION'], echo=CONFIG['SQL_LOGGING'])
db_session = Session(bind=engine)


def init_tables(db_engine):
    Base.metadata.create_all(db_engine)


def auto_str(cls):
    def __str__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )

    cls.__str__ = __str__
    return cls


@auto_str
class LoggedMessage(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, nullable=False)
    message_uid = Column(String(length=250), nullable=False)
    message_content = Column(String(), nullable=False)
    author = Column(Integer, ForeignKey('users.id'), nullable=False)
    time_created = Column(DateTime, nullable=False)
    channel_name = Column(String(250), nullable=False)


@auto_str
class MessageDiff(Base):
    __tablename__ = 'message_edits'

    id = Column(Integer, primary_key=True, nullable=False)
    original_message = Column(Integer, ForeignKey('messages.id'), nullable=False)
    edit_content = Column(String(), nullable=False)
    time_created = Column(DateTime, nullable=False)


@auto_str
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, nullable=False)
    user_uid = Column(String(length=250), nullable=False)
    username = Column(String(length=50), nullable=False)
    first_seen = Column(DateTime, nullable=False, default=datetime.utcnow())
    last_seen = Column(DateTime, nullable=False, default=datetime.utcnow())
    uni_id = Column(String(length=20), nullable=True)
    verified_at = Column(DateTime, nullable=True)
