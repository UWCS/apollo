import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from karma.parser import parse_message, RawKarma
from models import Base


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


def test_empty(database):
    assert parse_message("", database) is None


def test_no_karma(database):
    assert parse_message("Hello, world!", database) is None


def test_no_karma_complex_sentence(database):
    assert (
        parse_message(
            "Hello, world! This is a test input string with 30+ characters", database
        )
        is None
    )


def test_empty_with_code_block(database):
    assert parse_message("```FoobarBaz```", database) is None


def test_empty_with_inline_block(database):
    assert parse_message("`FoobarBaz`", database) is None


def test_simple_positive(database):
    assert parse_message("Foobar++", database) == [
        RawKarma(name="Foobar", op="++", reason=None)
    ]


def test_simple_negative(database):
    assert parse_message("Foobar--", database) == [
        RawKarma(name="Foobar", op="--", reason=None)
    ]


def test_simple_neutral_pm(database):
    assert parse_message("Foobar+-", database) == [
        RawKarma(name="Foobar", op="+-", reason=None)
    ]


def test_simple_neutral_mp(database):
    assert parse_message("Foobar-+", database) == [
        RawKarma(name="Foobar", op="-+", reason=None)
    ]


def test_quoted_positive(database):
    assert parse_message('"Foobar"++', database) == [
        RawKarma(name="Foobar", op="++", reason=None)
    ]


def test_quoted_negative(database):
    assert parse_message('"Foobar"--', database) == [
        RawKarma(name="Foobar", op="--", reason=None)
    ]


def test_quoted_neutral_pm(database):
    assert parse_message('"Foobar"+-', database) == [
        RawKarma(name="Foobar", op="+-", reason=None)
    ]


def test_quoted_sentence_neutral_pm(database):
    assert parse_message('"Foobar Baz"+-', database) == [
        RawKarma(name="Foobar Baz", op="+-", reason=None)
    ]


def test_quoted_neutral_mp(database):
    assert parse_message('"Foobar"-+', database) == [
        RawKarma(name="Foobar", op="-+", reason=None)
    ]


def test_simple_positive_with_text_after(database):
    assert parse_message("Foobar++ since it's pretty cool", database) == [
        RawKarma(name="Foobar", op="++", reason=None)
    ]


def test_simple_positive_with_text_before(database):
    assert parse_message("Since its pretty cool, foobar++", database) == [
        RawKarma(name="foobar", op="++", reason=None)
    ]


def test_simple_positive_with_paren_reason(database):
    assert parse_message("Foobar++ (hella cool)", database) == [
        RawKarma(name="Foobar", op="++", reason="hella cool")
    ]


def test_simple_positive_with_quote_reason(database):
    assert parse_message('Foobar++ "\'hella cool"', database) == [
        RawKarma(name="Foobar", op="++", reason="'hella cool")
    ]


def test_simple_positive_with_paren_reason_and_comma(database):
    assert parse_message("Foobar++ (hella, cool)", database) == [
        RawKarma(name="Foobar", op="++", reason="hella, cool")
    ]


def test_simple_positive_with_empty_paren_reason(database):
    assert parse_message("Foobar++ ()", database) == [
        RawKarma(name="Foobar", op="++", reason=None)
    ]


def test_simple_positive_with_compound_reason(database):
    assert parse_message("Foobar++ because it is (hella cool)", database) == [
        RawKarma(name="Foobar", op="++", reason="it is (hella cool)")
    ]


def test_simple_positive_with_compound_reason_comma(database):
    assert parse_message("Foobar++ because it, is (hella cool)", database) == [
        RawKarma(name="Foobar", op="++", reason="it")
    ]


def test_simple_positive_with_reason(database):
    assert parse_message("Foobar++ because baz", database) == [
        RawKarma(name="Foobar", op="++", reason="baz")
    ]


def test_simple_positive_with_reason_quoted(database):
    assert parse_message('Foobar++ because "baz"', database) == [
        RawKarma(name="Foobar", op="++", reason="baz")
    ]


def test_simple_positive_with_reason_quoted_comma(database):
    assert parse_message('Foobar++ because "baz, blat"', database) == [
        RawKarma(name="Foobar", op="++", reason="baz, blat")
    ]


def test_simple_negative_with_reason(database):
    assert parse_message("Foobar-- because baz", database) == [
        RawKarma(name="Foobar", op="--", reason="baz")
    ]


def test_simple_neutral_pm_with_reason(database):
    assert parse_message("Foobar+- because baz", database) == [
        RawKarma(name="Foobar", op="+-", reason="baz")
    ]


def test_simple_neutral_mp_with_reason(database):
    assert parse_message("Foobar-+ because baz", database) == [
        RawKarma(name="Foobar", op="-+", reason="baz")
    ]


def test_quoted_positive_with_reason(database):
    assert parse_message('"Foobar"++ because baz', database) == [
        RawKarma(name="Foobar", op="++", reason="baz")
    ]


def test_quoted_negative_with_reason(database):
    assert parse_message('"Foobar"-- because baz', database) == [
        RawKarma(name="Foobar", op="--", reason="baz")
    ]


def test_quoted_neutral_pm_with_reason(database):
    assert parse_message('"Foobar"+- because baz', database) == [
        RawKarma(name="Foobar", op="+-", reason="baz")
    ]


def test_quoted_neutral_mp_with_reason(database):
    assert parse_message('"Foobar"-+ because baz', database) == [
        RawKarma(name="Foobar", op="-+", reason="baz")
    ]


def test_simple_multiple_karma(database):
    assert parse_message("Foobar++, Baz-- Blat+-", database) == [
        RawKarma(name="Foobar", op="++", reason=None),
        RawKarma(name="Baz", op="--", reason=None),
        RawKarma(name="Blat", op="+-", reason=None),
    ]


def test_simple_multiple_karma_with_reasons_and_quotes(database):
    assert parse_message('Foobar++ because baz blat, "Hello world"--', database) == [
        RawKarma(name="Foobar", op="++", reason="baz blat"),
        RawKarma(name="Hello world", op="--", reason=None),
    ]


def test_complex_multiple_karma_no_reasons_quotes(database):  # The Sinjo input
    assert parse_message('Foobar++ "Hello world"--', database) == [
        RawKarma(name="Foobar", op="++", reason=None),
        RawKarma(name="Hello world", op="--", reason=None),
    ]


def test_complex_multiple_karma_with_reasons_and_quotes(database):
    assert parse_message(
        'Foobar++ because baz blat, "Hello world"-- for "foo, bar"', database
    ) == [
        RawKarma(name="Foobar", op="++", reason="baz blat"),
        RawKarma(name="Hello world", op="--", reason="foo, bar"),
    ]


def test_karma_op_no_token(database):
    assert parse_message("++", database) is None


def test_simple_invalid(database):
    assert parse_message("Foo+", database) is None


def test_simple_invalid_with_reason(database):
    assert parse_message("Foo+ because baz", database) is None


def test_simple_quoted_invalid_with_reason(database):
    assert parse_message('"Foo" because baz', database) is None


def test_string_starts_quoted_no_karma(database):
    assert (
        parse_message(
            '"Starting the sentence with a quote but there is no karma here', database
        )
        is None
    )


def test_start_simple_mid_message(database):
    assert parse_message(
        "Hello, world! Foo++ this is a mid-message karma", database
    ) == [RawKarma(name="Foo", op="++", reason=None)]


def test_start_simple_mid_message_with_reason(database):
    assert parse_message(
        "Hello, world! Foo++ because bar, this is a mid-message karma", database
    ) == [RawKarma(name="Foo", op="++", reason="bar")]


def test_code_block_with_internal_reason(database):
    assert parse_message("```Foobar++ baz because foo```", database) is None


def test_code_block_with_karma_op_after(database):
    assert parse_message("```Foobar baz```++", database) is None


def test_code_block_external_reason(database):
    assert parse_message("```Foobar baz``` because foo", database) is None


def test_code_block_with_karma_op_after_and_external_reason(database):
    assert parse_message("```Foobar baz```++ because foo", database) is None
