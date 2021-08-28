import os
from datetime import datetime

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cogs.commands.quotes import (
    QuoteError,
    QuoteException,
    add_quote,
    delete_quote,
    opt_in_to_quotes,
    opt_out_of_quotes,
    purge_quotes,
    quote_str,
    quotes_query,
    update_quote,
)
from models import Base, Quote, QuoteOptouts, User
from utils.mentions import MentionType, MentionConverter, Mention

TEST_QUOTES = [
    Quote.id_quote(1, "talking to myself!", datetime(2018, 10, 11)),
    Quote.string_quote(
        "ircguy", "talking to myself! on irc!", datetime(2018, 10, 12)
    ),
    Quote.id_quote(2, "talking to someone else!", datetime(2018, 10, 13)),
    Quote.string_quote(
        "ircguy", "talking to someone else! on irc!", datetime(2018, 10, 14)
    ),
    Quote.id_quote(
        1, "taking about someone else! from irc!", datetime(2018, 10, 15)
    ),
    Quote.string_quote(
        "ircguy2", "something about FOSS idk", datetime(2018, 10, 16)
    ),
]


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

    # Add three users
    users = [
        User(user_uid=1000, username="Foo"),
        User(user_uid=1337, username="Bar"),
        User(user_uid=3000, username="NoQuoteMePls"),
    ]

    db_session.add_all(users)

    db_session.add_all(TEST_QUOTES)

    # Add some opt-outs
    db_session.add(QuoteOptouts(user_type=MentionType.ID, user_id=3, user_string=None))

    db_session.commit()
    return db_session


QUERY_QUOTES = {
    "By ID": ("#1", [TEST_QUOTES[0]]),
    "By Author (Discord)": ("<@!1337>", [TEST_QUOTES[2]]),
    "By Author (IRC/String)": ("@ircguy", [TEST_QUOTES[1], TEST_QUOTES[3]]),
    "By Topic": ("irc", [TEST_QUOTES[1], TEST_QUOTES[3], TEST_QUOTES[4]]),
    "No valid quotes": ("blargleargle", []),
}

ADD_QUOTES = {
    "Discord user quote": (
        Mention.id_mention(1),
        Mention.id_mention(1),
        "Foo said this",
        datetime(1998, 12, 24),
        "#7",
        '**#7:** "Foo said this" - <@1000> (24/12/1998)',
        7,
    ),
    "Unregistered user quote": (
        Mention.id_mention(1),
        "<@!1034>",
        "Unknown user said this",
        datetime(1998, 12, 24),
        "#8",
        '**#8:** "Unknown user said this" - <@!1034> (24/12/1998)',
        8,
    ),
    "IRC user/string quote": (
        "Barfoo",
        "Foobar",
        "Foobar said this",
        datetime(1998, 12, 24),
        "#9",
        '**#9:** "Foobar said this" - Foobar (24/12/1998)',
        9,
    ),
}

ADD_FAIL = {
    "Add quote from opted out user": (
        "ircguy",
        "<@!3000>",
        "This is the one thing we didn't want to happen.",
        datetime(1984, 1, 1),
        QuoteError.OPTED_OUT,
        9,
    )
}

DELETE_QUOTES = {
    "Discord user deleting own quote": (
        False,
        Mention.id_mention(1),
        "#7",
        "#7",
        8,
    ),
    "Exec user deleting other quote": (
        True,
        "<@!3001>",
        "#8",
        "#8",
        7,
    ),
    "IRC/String user deleting their quote": (
        False,
        "Foobar",
        "#9",
        "#9",
        6,
    ),
}

DELETE_FAIL = {
    "Discord user deleting someone else's quote": (
        False,
        Mention.id_mention(1),
        "#3",
        QuoteError.NOT_PERMITTED,
        6,
    ),
    "Discord user deleting IRC user quote": (
        False,
        Mention.id_mention(1),
        "#2",
        QuoteError.NOT_PERMITTED,
        6,
    ),
    "IRC user deleting Discord user quote": (
        False,
        "ircguy",
        "#1",
        QuoteError.NOT_PERMITTED,
        6,
    ),
    "Delete non-existing quote": (
        False,
        Mention.id_mention(1),
        "#100",
        QuoteError.NOT_FOUND,
        6,
    ),
}

UPDATE_QUOTES = {
    "Discord user updating their quote": (
        False,
        Mention.id_mention(1),
        "#1",
        "updated quote",
        "#1",
        '**#1:** "updated quote" - <@1000> (11/10/2018)',
    ),
    "Exec updating someone else's quote": (
        True,
        "<@!3000>",
        "#3",
        "Exec updated this quote",
        "#3",
        '**#3:** "Exec updated this quote" - <@1337> (13/10/2018)',
    ),
    "IRC user updating their quote": (
        False,
        "ircguy",
        "#2",
        "Updated from IRC",
        "#2",
        '**#2:** "Updated from IRC" - ircguy (12/10/2018)',
    ),
}

UPDATE_FAIL = {
    "Discord user updating someone else's quote": (
        False,
        Mention.id_mention(1),
        "#3",
        "updated quote",
        QuoteError.NOT_PERMITTED,
        '**#3:** "Exec updated this quote" - <@1337> (13/10/2018)',
    ),
    "IRC user updating someone else's quote": (
        False,
        "ircguy",
        "#6",
        "Updated from IRC",
        QuoteError.NOT_PERMITTED,
        '**#6:** "something about FOSS idk" - ircguy2 (16/10/2018)',
    ),
    "Updating non-existing quote": (
        False,
        Mention.id_mention(1),
        "#100",
        "updating a non-quote",
        QuoteError.NOT_FOUND,
        None,
    ),
}

PURGE_QUOTES = {
    "Discord user self-purge": (
        False,
        "<@1000>",
        "<@1000>",
        "2",
        4,
    ),
    "Exec purging other user": (
        True,
        "<@3001>",
        "<@1337>",
        "1",
        3,
    ),
    "IRC user self-purge": (
        False,
        "ircguy",
        "ircguy",
        "2",
        1,
    ),
}

PURGE_FAIL = {
    "Discord user purging other user": (
        False,
        "<@1000>",
        "<@1337>",
        QuoteError.NOT_PERMITTED,
        1,
    ),
    "Purging author with no quotes": (
        False,
        "<@1000>",
        "<@1000>",
        QuoteError.NOT_FOUND,
        1,
    ),
}

OPTOUTS = {
    "Discord user opt-out": (
        False,
        "<@1000>",
        None,
        "0",
        2,
        1,
    ),
    "Exec opting out other user": (
        True,
        "<@3001>",
        "ircguy",
        "0",
        3,
        1,
    ),
}

OPTOUT_FAIL = {
    "Discord user opting out other user": (
        False,
        "<@1000>",
        "<@1337>",
        QuoteError.NOT_PERMITTED,
        3,
        1,
    )
}

OPTINS = {
    "Discord user opting in": (
        "<@1000>",
        "7",
        2,
        2,
    ),
    "IRC user opting in": (
        "ircguy",
        "8",
        1,
        3,
    ),
}

OPTIN_FAIL = {
    "Discord user opting in but has already opted in": (
        "<@1000>",
        "9",
        1,
        4,
    )
}


@pytest.mark.parametrize(
    ["query", "expected"], QUERY_QUOTES.values(), ids=QUERY_QUOTES.keys()
)
def test_query_quotes(database, query, expected):
    actual = quotes_query(query, database).all()
    assert actual == expected


@pytest.mark.parametrize(
    ["requester", "mention", "quote", "time", "new_id", "expected", "db_size"],
    ADD_QUOTES.values(),
    ids=ADD_QUOTES.keys(),
)
def test_add_quotes(
    database, requester, mention, quote, time, new_id, expected, db_size
):
    add_quote(requester, mention, quote, time, database)
    q = quotes_query(new_id, database).one_or_none()
    actual = quote_str(q)

    assert actual == expected
    assert database.query(Quote).count() == db_size


@pytest.mark.parametrize(
    ["requester", "mention", "quote", "time", "error", "db_size"],
    ADD_FAIL.values(),
    ids=ADD_FAIL.keys(),
)
def test_add_fails(database, requester, mention, quote, time, error, db_size):
    try:
        add_quote(requester, mention, quote, time, database)
    except QuoteException as e:
        assert e.err == error

    assert database.query(Quote).count() == db_size


@pytest.mark.parametrize(
    ["is_exec", "user", "to_delete", "expected", "db_size"],
    DELETE_QUOTES.values(),
    ids=DELETE_QUOTES.keys(),
)
def test_delete_quotes(database, is_exec, user, to_delete, expected, db_size):
    actual = delete_quote(is_exec, user, to_delete, database)

    assert actual == expected
    assert database.query(Quote).count() == db_size


@pytest.mark.parametrize(
    ["is_exec", "user", "to_delete", "error", "db_size"],
    DELETE_FAIL.values(),
    ids=DELETE_FAIL.keys(),
)
def test_delete_fails(database, is_exec, user, to_delete, error, db_size):
    try:
        delete_quote(is_exec, user, to_delete, database)
    except QuoteException as e:
        assert e.err == error

    assert database.query(Quote).count() == db_size


@pytest.mark.parametrize(
    ["is_exec", "user", "to_update", "new_text", "expected", "expected_quote"],
    UPDATE_QUOTES.values(),
    ids=UPDATE_QUOTES.keys(),
)
def test_update_quotes(
    database, is_exec, user, to_update, new_text, expected, expected_quote
):
    actual = update_quote(is_exec, user, to_update, new_text, database)
    actual_quote = quote_str(quotes_query(to_update, database).one_or_none())

    assert actual == expected
    assert actual_quote == expected_quote


@pytest.mark.parametrize(
    ["is_exec", "user", "to_update", "new_text", "error", "expected_quote"],
    UPDATE_FAIL.values(),
    ids=UPDATE_FAIL.keys(),
)
def test_update_fails(
    database, is_exec, user, to_update, new_text, error, expected_quote
):

    try:
        update_quote(is_exec, user, to_update, new_text, database)
    except QuoteException as e:
        assert e.err == error

    actual_quote = quote_str(quotes_query(to_update, database).one_or_none())
    assert actual_quote == expected_quote


@pytest.mark.parametrize(
    ["is_exec", "user", "target", "expected", "db_size"],
    PURGE_QUOTES.values(),
    ids=PURGE_QUOTES.keys(),
)
def test_purge_quotes(database, is_exec, user, target, expected, db_size):
    actual = purge_quotes(is_exec, user, target, database)

    assert actual == expected
    assert database.query(Quote).count() == db_size


@pytest.mark.parametrize(
    ["is_exec", "user", "target", "error", "db_size"],
    PURGE_FAIL.values(),
    ids=PURGE_FAIL.keys(),
)
def test_purge_fails(database, is_exec, user, target, error, db_size):
    try:
        purge_quotes(is_exec, user, target, database)
    except QuoteException as e:
        assert e == error

    assert database.query(Quote).count() == db_size


@pytest.mark.parametrize(
    ["is_exec", "requester", "target", "expected", "oo_size", "q_size"],
    OPTOUTS.values(),
    ids=OPTOUTS.keys(),
)
def test_optout(database, is_exec, requester, target, expected, oo_size, q_size):
    if target is None:
        target = requester

    actual = opt_out_of_quotes(is_exec, requester, target, database)

    try:
        add_quote(requester, target, "quote thingy", datetime.now(), database)
    except QuoteException as e:
        assert e.err == QuoteError.OPTED_OUT

    assert actual == expected
    assert database.query(QuoteOptouts).count() == oo_size
    assert database.query(Quote).count() == q_size


@pytest.mark.parametrize(
    ["is_exec", "requester", "target", "error", "oo_size", "q_size"],
    OPTOUT_FAIL.values(),
    ids=OPTOUT_FAIL.keys(),
)
def test_optout_fails(database, is_exec, requester, target, error, oo_size, q_size):
    if target is None:
        target = requester

    try:
        opt_out_of_quotes(is_exec, requester, target, database)
    except QuoteException as e:
        assert e.err == error

    assert database.query(QuoteOptouts).count() == oo_size
    assert database.query(Quote).count() == q_size


@pytest.mark.parametrize(
    ["requester", "try_quote", "oo_size", "q_size"], OPTINS.values(), ids=OPTINS.keys()
)
def test_optin(database, requester, try_quote, oo_size, q_size):

    opt_in_to_quotes(requester, database)
    actual_from_quote = add_quote(
        requester, requester, "quote thingy", datetime.now(), database
    )

    assert database.query(QuoteOptouts).count() == oo_size
    assert actual_from_quote == try_quote
    assert database.query(Quote).count() == q_size


@pytest.mark.parametrize(
    ["requester", "try_quote", "oo_size", "q_size"],
    OPTIN_FAIL.values(),
    ids=OPTIN_FAIL.keys(),
)
def test_optin_fails(database, requester, try_quote, oo_size, q_size):

    try:
        opt_in_to_quotes(requester, database)
    except QuoteException as e:
        e.err == QuoteError.NO_OP

    actual_from_quote = add_quote(
        requester, requester, "quote thingy", datetime.now(), database
    )

    assert database.query(QuoteOptouts).count() == oo_size
    assert actual_from_quote == try_quote
    assert database.query(Quote).count() == q_size
