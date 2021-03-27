import os
from textwrap import dedent

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from karma.parser import KarmaTransaction, Operation, parse_message
from models import Base
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

    return db_session


TEST_CASES = {
    # Cases with no karma
    "empty": (make_message_stub(""), None),
    "no karma": (make_message_stub("Hello, world!"), None),
    "no karma long sentence": (
        make_message_stub(
            "Hello, world! This is a test input string with 30+ characters"
        ),
        None,
    ),
    "no karma unbalanced quoted": (make_message_stub('"foo bar baz'), None),
    "no karma topic": (make_message_stub("++"), None),
    "too short operator": (make_message_stub("foobar+"), None),
    "too long operator": (make_message_stub('"foobar"++++'), None),
    "unrecognised operator": (make_message_stub("foobar=="), None),
    "no karma operator with reason": (make_message_stub('"foobar" for reason'), None),
    # Cases with no karma because of code blocks
    "no karma code block": (
        make_message_stub("```foobar++```"),
        None,
    ),
    "no karma multi-line code block": (
        make_message_stub(
            dedent(
                """
                ```
                example
                multi
                line
                foobar++
                code
                block
                ```
                """
            )
        ),
        None,
    ),
    "no karma multi-line code block with text before": (
        make_message_stub(
            dedent(
                """
                text before code block```
                code
                block
                ```++
                """
            )
        ),
        None,
    ),
    # Simple karma cases
    "simple add": (
        make_message_stub("foobar++"),
        [KarmaTransaction("foobar", False, Operation.POSITIVE, None)],
    ),
    "simple neutral +-": (
        make_message_stub("foobar+-"),
        [KarmaTransaction("foobar", False, Operation.NEUTRAL, None)],
    ),
    "simple neutral -+": (
        make_message_stub("foobar-+"),
        [KarmaTransaction("foobar", False, Operation.NEUTRAL, None)],
    ),
    "simple negative": (
        make_message_stub("foobar--"),
        [KarmaTransaction("foobar", False, Operation.NEGATIVE, None)],
    ),
    "quoted": (
        make_message_stub('"foobar"++'),
        [KarmaTransaction("foobar", False, Operation.POSITIVE, None)],
    ),
    "quoted with space": (
        make_message_stub('"foo bar"++'),
        [KarmaTransaction("foo bar", False, Operation.POSITIVE, None)],
    ),
    "simple with text after": (
        make_message_stub("foobar++ baz quz quz"),
        [KarmaTransaction("foobar", False, Operation.POSITIVE, None)],
    ),
    "simple with text before": (
        make_message_stub("baz quz qux foobar++"),
        [KarmaTransaction("foobar", False, Operation.POSITIVE, None)],
    ),
    "simple inside text": (
        make_message_stub("baz quz foobar++ qux"),
        [KarmaTransaction("foobar", False, Operation.POSITIVE, None)],
    ),
    # Karma reasons
    "paren (reason)": (
        make_message_stub("foobar++ (reason)"),
        [KarmaTransaction("foobar", False, Operation.POSITIVE, "reason")],
    ),
    'quote "reason"': (
        make_message_stub('foobar++ "reason"'),
        [KarmaTransaction("foobar", False, Operation.POSITIVE, "reason")],
    ),
    "for reason": (
        make_message_stub("foobar++ for reason"),
        [KarmaTransaction("foobar", False, Operation.POSITIVE, "reason")],
    ),
    "because reason": (
        make_message_stub("foobar++ because reason"),
        [KarmaTransaction("foobar", False, Operation.POSITIVE, "reason")],
    ),
    "paren (reason, comma)": (
        make_message_stub("foobar++ (reason, comma)"),
        [KarmaTransaction("foobar", False, Operation.POSITIVE, "reason, comma")],
    ),
    "empty paren reason": (
        make_message_stub("foobar++ ()"),
        [KarmaTransaction("foobar", False, Operation.POSITIVE, None)],
    ),
    "for reason with parens": (
        make_message_stub("foobar++ for reason (parens)"),
        [KarmaTransaction("foobar", False, Operation.POSITIVE, "reason (parens)")],
    ),
    "for reason with comma": (
        # An early comma will cut the karma reason short
        make_message_stub("foobar++ for reason, comma"),
        [KarmaTransaction("foobar", False, Operation.POSITIVE, "reason")],
    ),
    "for quoted reason": (
        make_message_stub('foobar++ for "reason"'),
        [KarmaTransaction("foobar", False, Operation.POSITIVE, "reason")],
    ),
    "for quoted reason with comma": (
        make_message_stub('foobar++ for "reason, comma"'),
        [KarmaTransaction("foobar", False, Operation.POSITIVE, "reason, comma")],
    ),
    "for quoted reason with space": (
        make_message_stub('foobar++ for "reason reason"'),
        [KarmaTransaction("foobar", False, Operation.POSITIVE, "reason reason")],
    ),
    "mid sentence for reason": (
        make_message_stub("Hello, world! foobar++ for reason, rest of sentence"),
        [KarmaTransaction("foobar", False, Operation.POSITIVE, "reason")],
    ),
    # Multiple karma
    "multiple karma": (
        make_message_stub("foo++ bar-- baz+- quz-+"),
        [
            KarmaTransaction("foo", False, Operation.POSITIVE, None),
            KarmaTransaction("bar", False, Operation.NEGATIVE, None),
            KarmaTransaction("baz", False, Operation.NEUTRAL, None),
            KarmaTransaction("quz", False, Operation.NEUTRAL, None),
        ],
    ),
    "multiple karma comma-separated": (
        make_message_stub("foo++, bar--, baz+-, quz-+"),
        [
            KarmaTransaction("foo", False, Operation.POSITIVE, None),
            KarmaTransaction("bar", False, Operation.NEGATIVE, None),
            KarmaTransaction("baz", False, Operation.NEUTRAL, None),
            KarmaTransaction("quz", False, Operation.NEUTRAL, None),
        ],
    ),
    "multiple quoted karma": (
        make_message_stub('"item 1"++ "item 2"++'),
        [
            KarmaTransaction("item 1", False, Operation.POSITIVE, None),
            KarmaTransaction("item 2", False, Operation.POSITIVE, None),
        ],
    ),
    "multiple karma with parens reasons": (
        make_message_stub("item1++ (reason1) item2++ (reason2)"),
        [
            KarmaTransaction("item1", False, Operation.POSITIVE, "reason1"),
            KarmaTransaction("item2", False, Operation.POSITIVE, "reason2"),
        ],
    ),
    "multiple karma with parens reasons comma-separated": (
        make_message_stub("item1++ (reason1), item2++ (reason2)"),
        [
            KarmaTransaction("item1", False, Operation.POSITIVE, "reason1"),
            KarmaTransaction("item2", False, Operation.POSITIVE, "reason2"),
        ],
    ),
    "multiple karma with for reasons": (
        # Karma with for/because reasons but be separated with commas due to the way parsing works
        make_message_stub("item1++ for reason1, item2++ for reason2"),
        [
            KarmaTransaction("item1", False, Operation.POSITIVE, "reason1"),
            KarmaTransaction("item2", False, Operation.POSITIVE, "reason2"),
        ],
    ),
    "multiple karma with quote reasons": (
        make_message_stub('item1++ "reason 1" item2++ "reason 2"'),
        [
            KarmaTransaction("item1", False, Operation.POSITIVE, "reason 1"),
            KarmaTransaction("item2", False, Operation.POSITIVE, "reason 2"),
        ],
    ),
    "multiple karma with mixed reasons": (
        make_message_stub(
            'item1++ for reason1, item2++ because reason2, item3++ (reason 3), item4++ "reason 4"'
        ),
        [
            KarmaTransaction("item1", False, Operation.POSITIVE, "reason1"),
            KarmaTransaction("item2", False, Operation.POSITIVE, "reason2"),
            KarmaTransaction("item3", False, Operation.POSITIVE, "reason 3"),
            KarmaTransaction("item4", False, Operation.POSITIVE, "reason 4"),
        ],
    ),
}


# A note on parametrised tests/table testing:
# Don't change the test to add a new case - the test itself should be as simple as possible.
# If adding a new test case would require changes to this test, it would be better suited as a new test function.
@pytest.mark.parametrize(
    ["message", "expected"], TEST_CASES.values(), ids=TEST_CASES.keys()
)
def test_parser(database, message, expected):
    actual = parse_message(message, database)
    assert actual == expected
