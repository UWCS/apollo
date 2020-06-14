import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from karma.parser import RawKarma, parse_message
from models import Base, BlockedKarma, User


@pytest.fixture(scope="module")
def database():
    # Locate the testing config for Alembic
    config = Config(os.path.join(os.path.dirname(__file__), "../alembic.tests.ini"))

    # Set the migration secret key here
    if not os.environ.get("SECRET_KEY", None):
        os.environ["SECRET_KEY"] = "test"

    # Start up the in-memory database instance
    db_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(db_engine)
    db_session = Session(bind=db_engine)

    # Mark it as up-to-date with migrations
    command.stamp(config, "head")

    # Add some blacklisted karma items and a user who added them
    user = User(user_uid=1, username="Foo")
    db_session.add(user)

    c = BlockedKarma(topic="c".casefold(), user_id=1)
    notepad = BlockedKarma(topic="notepad".casefold(), user_id=1)
    db_session.add_all([c, notepad])
    db_session.commit()

    return db_session


def test_blacklist_blank(database):
    assert parse_message("", database) is None


def test_single_not_in_blacklist(database):
    assert parse_message("foo++", database) == [
        RawKarma(name="foo", op="++", reason=None)
    ]


def test_blacklist_single_blocked_lower(database):
    assert parse_message("c++", database) is None


def test_blacklist_single_blocked_upper(database):
    assert parse_message("C++", database) is None


def test_blacklist_single_allowed_lower(database):
    assert parse_message('"c"++', database) == [
        RawKarma(name="c", op="++", reason=None)
    ]


def test_blacklist_single_allowed_upper(database):
    assert parse_message('"C"++', database) == [
        RawKarma(name="C", op="++", reason=None)
    ]


def test_blacklist_single_blocked_mixed(database):
    assert parse_message("NoTepAD++", database) is None


def test_blacklist_single_allowed_mixed(database):
    assert parse_message('"NoTepAD"++', database) == [
        RawKarma(name="NoTepAD", op="++", reason=None)
    ]


def test_blacklist_single_karma_quoted(database):
    assert parse_message('"c++"', database) is None


def test_multiple_not_in_blacklist(database):
    assert parse_message("foo++ bar++", database) == [
        RawKarma(name="foo", op="++", reason=None),
        RawKarma(name="bar", op="++", reason=None),
    ]


def test_blacklist_multiple_blocked(database):
    assert parse_message("c++ notepad++", database) is None


def test_blacklist_multiple_allowed(database):
    assert parse_message('"c"++ "notepad"++', database) == [
        RawKarma(name="c", op="++", reason=None),
        RawKarma(name="notepad", op="++", reason=None),
    ]


def test_blacklist_mixed_allowed(database):
    assert parse_message('"c"++ notepad++', database) == [
        RawKarma(name="c", op="++", reason=None)
    ]


def test_blacklist_mixed_quoted_all_blocked(database):
    assert parse_message('"c++" notepad++', database) is None


def test_blacklist_mixed_quoted_allowed(database):
    assert parse_message('"c++" "notepad"++', database) == [
        RawKarma(name="notepad", op="++", reason=None)
    ]
