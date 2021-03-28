import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from karma.parser import KarmaTransaction, Operation, RawKarma, parse_message
from models import Base, BlockedKarma, User
from tests.stubs import make_message_stub


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

    c = BlockedKarma(topic="c", user_id=1)
    notepad = BlockedKarma(topic="notepad", user_id=1)
    db_session.add_all([c, notepad])
    db_session.commit()

    return db_session


TEST_CASES = {
    # Make sure the blacklist does not interfere with regular karma parsing
    "not in blacklist": (
        make_message_stub("foobar++"),
        [KarmaTransaction("foobar", False, Operation.POSITIVE, None)],
    ),
    # Items that are on the blacklist and it blocks
    "blacklisted item same case": (make_message_stub("notepad++"), None),
    "blacklisted item different case": (make_message_stub("NOTEPAD++"), None),
    "blacklisted short item same case": (make_message_stub("c++"), None),
    "blacklisted short item different case": (make_message_stub("C++"), None),
    "blacklisted item with reason": (make_message_stub("notepad++ for reason"), None),
    # Items on the blacklist that are bypassed
    "blacklist bypass": (
        make_message_stub('"notepad"++'),
        [KarmaTransaction("notepad", False, Operation.POSITIVE, None)],
    ),
    "blacklist bypass short item": (
        make_message_stub('"c"++'),
        [KarmaTransaction("c", False, Operation.POSITIVE, None)],
    ),
    "blacklist bypass with reason": (
        make_message_stub('"notepad"++ for reason'),
        [KarmaTransaction("notepad", False, Operation.POSITIVE, "reason")],
    ),
    # Mixture of blacklist and non-blacklist items
    "blacklisted item and non-blacklisted item": (
        make_message_stub("notepad++ foobar++"),
        [KarmaTransaction("foobar", False, Operation.POSITIVE, None)],
    ),
}


# A note on parametrised tests/table testing:
# Don't change the test to add a new case - the test itself should be as simple as possible.
# If adding a new test case would require changes to this test, it would be better suited as a new test function.
@pytest.mark.parametrize(
    ["message", "expected"], TEST_CASES.values(), ids=TEST_CASES.keys()
)
def test_blacklist(database, message, expected):
    actual = parse_message(message, database)
    assert actual == expected
