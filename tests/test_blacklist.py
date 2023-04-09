import os
from typing import Tuple

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from karma.parser import KarmaItem, KarmaOperation
from karma.transaction import KarmaTransaction, apply_blacklist
from models import Base, BlockedKarma, User


@pytest.fixture(scope="module")
def database():
    # Locate the testing config for Alembic
    config = Config(os.path.join(os.path.dirname(__file__), "../alembic.tests.ini"))

    # Set the migration secret key here
    if not os.environ.get("SECRET_KEY", None):
        os.environ["SECRET_KEY"] = "test"

    # Start up the in-memory database instance
    db_engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(db_engine)
    db_session = Session(bind=db_engine, future=True)

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


TEST_CASES: dict[str, Tuple[list[KarmaTransaction], list[KarmaTransaction]]] = {
    # Make sure the blacklist does not interfere with regular karma parsing
    "not in blacklist": (
        [KarmaTransaction(KarmaItem("foobar", KarmaOperation.POSITIVE, None), False)],
        [KarmaTransaction(KarmaItem("foobar", KarmaOperation.POSITIVE, None), False)],
    ),
    # Items that are on the blacklist and it blocks
    "blacklisted item same case": (
        [KarmaTransaction(KarmaItem("notepad", KarmaOperation.POSITIVE, None), False)],
        [],
    ),
    "blacklisted item different case": (
        [KarmaTransaction(KarmaItem("NOTEPAD", KarmaOperation.POSITIVE, None), False)],
        [],
    ),
    "blacklisted item with reason": (
        [
            KarmaTransaction(
                KarmaItem("notepad", KarmaOperation.POSITIVE, "reason"), False
            )
        ],
        [],
    ),
    # Items on the blacklist that are bypassed
    "blacklist bypass": (
        [
            KarmaTransaction(
                KarmaItem("notepad", KarmaOperation.POSITIVE, None, True), False
            )
        ],
        [
            KarmaTransaction(
                KarmaItem("notepad", KarmaOperation.POSITIVE, None, True), False
            )
        ],
    ),
    "blacklist bypass short item": (
        [KarmaTransaction(KarmaItem("c", KarmaOperation.POSITIVE, None, True), False)],
        [KarmaTransaction(KarmaItem("c", KarmaOperation.POSITIVE, None, True), False)],
    ),
    "blacklist bypass with reason": (
        [
            KarmaTransaction(
                KarmaItem("notepad", KarmaOperation.POSITIVE, "reason", True), False
            )
        ],
        [
            KarmaTransaction(
                KarmaItem("notepad", KarmaOperation.POSITIVE, "reason", True), False
            )
        ],
    ),
    # Mixture of blacklist and non-blacklist items
    "blacklisted item and non-blacklisted item": (
        [
            KarmaTransaction(
                KarmaItem("notepad", KarmaOperation.POSITIVE, None), False
            ),
            KarmaTransaction(KarmaItem("foobar", KarmaOperation.POSITIVE, None), False),
        ],
        [KarmaTransaction(KarmaItem("foobar", KarmaOperation.POSITIVE, None), False)],
    ),
}


# A note on parametrised tests/table testing:
# Don't change the test to add a new case - the test itself should be as simple as possible.
# If adding a new test case would require changes to this test, it would be better suited as a new test function.
@pytest.mark.parametrize(
    ["transactions", "expected"], TEST_CASES.values(), ids=TEST_CASES.keys()
)
def test_blacklist(database, transactions, expected):
    actual = apply_blacklist(transactions, database)
    assert actual == expected
