from datetime import datetime

from pytz import timezone, utc
from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    create_engine,
    ForeignKey,
    BigInteger,
    func,
    Boolean,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Session, relationship
from sqlalchemy_utils import EncryptedType, ScalarListType

from config import CONFIG

Base = declarative_base()

engine = create_engine(CONFIG["DATABASE_CONNECTION"], echo=CONFIG["SQL_LOGGING"])
db_session = Session(bind=engine)


def auto_str(cls):
    def __str__(self):
        return "%s(%s)" % (
            type(self).__name__,
            ", ".join("%s=%s" % item for item in vars(self).items()),
        )

    cls.__str__ = __str__
    return cls


@auto_str
class MessageDiff(Base):
    __tablename__ = "message_edits"

    id = Column(Integer, primary_key=True, nullable=False)
    original_message = Column(Integer, ForeignKey("messages.id"), nullable=False)
    new_content = Column(
        EncryptedType(type_in=String, key=CONFIG["BOT_SECRET_KEY"]), nullable=False
    )
    created_at = Column(DateTime, nullable=False)

    original = relationship("LoggedMessage", back_populates="edits")


@auto_str
class LoggedMessage(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, nullable=False)
    message_uid = Column(BigInteger, nullable=False)
    message_content = Column(
        EncryptedType(type_in=String, key=CONFIG["BOT_SECRET_KEY"]), nullable=False
    )
    author = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    channel_name = Column(
        EncryptedType(type_in=String, key=CONFIG["BOT_SECRET_KEY"]), nullable=False
    )

    user = relationship("User", back_populates="messages")
    edits = relationship(
        "MessageDiff", back_populates="original", order_by=MessageDiff.created_at
    )
    karma = relationship("KarmaChange", back_populates="message")


@auto_str
class KarmaChange(Base):
    __tablename__ = "karma_changes"

    karma_id = Column(Integer, ForeignKey("karma.id"), primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True, nullable=False)
    message_id = Column(
        Integer, ForeignKey("messages.id"), primary_key=True, nullable=False
    )
    created_at = Column(DateTime, nullable=False)
    # Using a Greek question mark (;) instead of a semicolon here!
    reasons = Column(ScalarListType(str, separator=";"), nullable=True)
    change = Column(Integer, nullable=False)
    score = Column(Integer, nullable=False)

    karma = relationship("Karma", back_populates="changes")
    user = relationship("User", back_populates="karma_changes")
    message = relationship("LoggedMessage", back_populates="karma")

    @hybrid_property
    def local_time(self):
        return utc.localize(self.created_at).astimezone(timezone("Europe/London"))


@auto_str
class Karma(Base):
    __tablename__ = "karma"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    added = Column(
        EncryptedType(type_in=DateTime, key=CONFIG["BOT_SECRET_KEY"]),
        nullable=False,
        default=datetime.utcnow(),
    )
    pluses = Column(Integer, nullable=False, default=0)
    minuses = Column(Integer, nullable=False, default=0)
    neutrals = Column(Integer, nullable=False, default=0)

    changes = relationship(
        "KarmaChange", back_populates="karma", order_by=KarmaChange.created_at.asc()
    )

    @hybrid_property
    def net_score(self):
        return self.pluses - self.minuses

    @hybrid_property
    def total_karma(self):
        return self.pluses + self.minuses + self.neutrals


@auto_str
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, nullable=False)
    user_uid = Column(BigInteger, nullable=False)
    username = Column(
        EncryptedType(type_in=String, key=CONFIG["BOT_SECRET_KEY"]), nullable=False
    )
    first_seen = Column(DateTime, nullable=False, default=datetime.utcnow())
    last_seen = Column(DateTime, nullable=False, default=datetime.utcnow())
    uni_id = Column(
        EncryptedType(type_in=String, key=CONFIG["BOT_SECRET_KEY"]), nullable=True
    )
    verified_at = Column(
        EncryptedType(type_in=DateTime, key=CONFIG["BOT_SECRET_KEY"]), nullable=True
    )

    messages = relationship(
        "LoggedMessage", back_populates="user", order_by=LoggedMessage.created_at
    )
    karma_changes = relationship(
        "KarmaChange", back_populates="user", order_by=KarmaChange.created_at
    )


@auto_str
class FilamentType(Base):
    FILLAMENTUM = "fillamentum"
    PRUSAMENT = "prusament"

    __tablename__ = "filament_types"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(Text, nullable=False, unique=True)
    profile = Column(String, default=FILLAMENTUM)
    image_path = Column(String, nullable=False, unique=True)

    @staticmethod
    def verify_type(type_str: str) -> bool:
        return {FilamentType.FILLAMENTUM: True, FilamentType.PRUSAMENT: True}.get(
            type_str.lower(), False
        )


@auto_str
class IgnoredChannel(Base):
    __tablename__ = "ignored_channels"

    channel = Column(BigInteger, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    added_at = Column(DateTime, nullable=False, default=func.current_timestamp())


@auto_str
class BlockedKarma(Base):
    __tablename__ = "blacklist"

    topic = Column(String, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    added_at = Column(DateTime, nullable=False, default=func.current_timestamp())


@auto_str
class Reminder(Base):
    __tablename__ = "reminders"
    id = Column(Integer, primary_key=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reminder_content = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    trigger_at = Column(DateTime, nullable=False)
    triggered = Column(Boolean, nullable=False)
    playback_channel_id = Column(BigInteger, nullable=False)
    irc_name = Column(String, nullable=True)
