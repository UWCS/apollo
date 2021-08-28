import os
from datetime import datetime

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cogs.commands.quotes import (
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
from utils.mentions import MentionType, parse_mention

TEST_QUOTES = [
    Quote(
        author_type=MentionType.ID,
        author_id=1,
        author_string=None,
        quote="talking to myself!",
        created_at=datetime(2018, 10, 11),
        edited_at=None,
    ),
    Quote(
        author_type=MentionType.STRING,
        author_id=None,
        author_string="ircguy",
        quote="talking to myself! on irc!",
        created_at=datetime(2018, 10, 12),
        edited_at=None,
    ),
    Quote(
        author_type=MentionType.ID,
        author_id=2,
        author_string=None,
        quote="talking to someone else!",
        created_at=datetime(2018, 10, 13),
        edited_at=None,
    ),
    Quote(
        author_type=MentionType.STRING,
        author_id=None,
        author_string="ircguy",
        quote="talking to someone else! on irc!",
        created_at=datetime(2018, 10, 14),
        edited_at=None,
    ),
    Quote(
        author_type=MentionType.ID,
        author_id=1,
        author_string=None,
        quote="talking about someone else! from irc!",
        created_at=datetime(2018, 10, 15),
        edited_at=None,
    ),
    Quote(
        author_type=MentionType.STRING,
        author_id=None,
        author_string="ircguy2",
        quote="something about FOSS idk",
        created_at=datetime(2018, 10, 16),
        edited_at=None,
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
    db_session.add(QuoteOptouts(user_type="id", user_id=3, user_string=None))

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
        "<@!1000>",
        "<@!1000>",
        "Foo said this",
        datetime(1998, 12, 24),
        "#7",
        '**#7:** "Foo said this" - <@1000> (24/12/1998)',
        7,
    ),
    "Unregistered user quote": (
        "<@!1000>",
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
    "Add quote from opted out user": (
        "ircguy",
        "<@!3000>",
        "This is the one thing we didn't want to happen.",
        datetime(1984, 1, 1),
        "#10",
        None,
        9,
    ),
}

DELETE_QUOTES = {
    "Discord user deleting own quote": (
        False,
        "<@!1000>",
        "#7",
        "Deleted quote with ID #7.",
        8,
    ),
    "Discord user deleting someone else's quote": (
        False,
        "<@!1000>",
        "#8",
        "You do not have permission to delete that quote.",
        8,
    ),
    "Exec user deleting other quote": (
        True,
        "<@!3001>",
        "#8",
        "Deleted quote with ID #8.",
        7,
    ),
    "IRC/String user deleting their quote": (
        False,
        "Foobar",
        "#9",
        "Deleted quote with ID #9.",
        6,
    ),
    "Discord user deleting IRC user quote": (
        False,
        "<@!1000>",
        "#2",
        "You do not have permission to delete that quote.",
        6,
    ),
    "IRC user deleting Discord user quote": (
        False,
        "ircguy",
        "#1",
        "You do not have permission to delete that quote.",
        6,
    ),
    "Delete non-existing quote": (
        False,
        "<@!1000>",
        "#100",
        "No quote with that ID was found.",
        6,
    ),
}

UPDATE_QUOTES = {
    "Discord user updating their quote": (
        False,
        "<@!1000>",
        "#1",
        "updated quote",
        "Updated quote with ID #1.",
        '**#1:** "updated quote" - <@1000> (11/10/2018)',
    ),
    "Discord user updating someone else's quote": (
        False,
        "<@!1000>",
        "#3",
        "updated quote",
        "You do not have permission to update that quote.",
        '**#3:** "talking to someone else!" - <@1337> (13/10/2018)',
    ),
    "Exec updating someone else's quote": (
        True,
        "<@!3000>",
        "#3",
        "Exec updated this quote",
        "Updated quote with ID #3.",
        '**#3:** "Exec updated this quote" - <@1337> (13/10/2018)',
    ),
    "IRC user updating their quote": (
        False,
        "ircguy",
        "#2",
        "Updated from IRC",
        "Updated quote with ID #2.",
        '**#2:** "Updated from IRC" - ircguy (12/10/2018)',
    ),
    "IRC user updating someone else's quote": (
        False,
        "ircguy",
        "#6",
        "Updated from IRC",
        "You do not have permission to update that quote.",
        '**#6:** "something about FOSS idk" - ircguy2 (16/10/2018)',
    ),
    "Updating non-existing quote": (
        False,
        "<@!1000>",
        "#100",
        "updating a non-quote",
        "No quote with that ID was found.",
        None,
    ),
}

PURGE_QUOTES = {
    "Discord user self-purge": (
        False,
        "<@1000>",
        "<@1000>",
        "Purged 2 quotes from author.",
        4,
    ),
    "Discord user purging other user": (
        False,
        "<@1000>",
        "<@1337>",
        "You do not have permission to purge this author.",
        4,
    ),
    "Exec purging other user": (
        True,
        "<@3001>",
        "<@1337>",
        "Purged 1 quotes from author.",
        3,
    ),
    "IRC user self-purge": (
        False,
        "ircguy",
        "ircguy",
        "Purged 2 quotes from author.",
        1,
    ),
    "Purging author with no quotes": (
        False,
        "<@1000>",
        "<@1000>",
        "Author has no quotes to purge.",
        1,
    ),
}

OPTOUTS = {
    "Discord user opt-out": (
        False,
        "<@1000>",
        None,
        "Author has no quotes to purge.\nUser has been opted out of quotes. They may opt in again later with the optin command.",
        "User has opted out of being quoted.",
        2,
        1,
    ),
    "Discord user opting out other user": (
        False,
        "<@1000>",
        "<@1337>",
        "You do not have permission to opt-out that user.",
        "Thanks <@1000>, I have saved this quote with the ID #7.",
        2,
        2,
    ),
    "Exec opting out other user": (
        True,
        "<@3001>",
        "ircguy",
        "Author has no quotes to purge.\nUser has been opted out of quotes. They may opt in again later with the optin command.",
        "User has opted out of being quoted.",
        3,
        2,
    ),
}

OPTINS = {
    "Discord user opting in": (
        "<@1000>",
        "Thanks <@1000>, I have saved this quote with the ID #8.",
        2,
        3,
    ),
    "Discord user opting in but has already opted in": (
        "<@1000>",
        "Thanks <@1000>, I have saved this quote with the ID #9.",
        2,
        4,
    ),
    "IRC user opting in": (
        "ircguy",
        "Thanks ircguy, I have saved this quote with the ID #10.",
        1,
        5,
    ),
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
    m = parse_mention(mention, database)
    add_quote(requester, m, quote, time, database)
    q = quotes_query(new_id, database).one_or_none()

    assert quote_str(q) == expected
    assert database.query(Quote).count() == db_size


@pytest.mark.parametrize(
    ["is_exec", "user", "to_delete", "expected", "db_size"],
    DELETE_QUOTES.values(),
    ids=DELETE_QUOTES.keys(),
)
def test_delete_quotes(database, is_exec, user, to_delete, expected, db_size):
    m = parse_mention(user, database)
    actual = delete_quote(is_exec, m, to_delete, database)

    assert actual == expected
    assert database.query(Quote).count() == db_size


@pytest.mark.parametrize(
    ["is_exec", "user", "to_update", "new_text", "expected", "expected_quote"],
    UPDATE_QUOTES.values(),
    ids=UPDATE_QUOTES.keys(),
)
def test_update_quotes(
    database, is_exec, user, to_update, new_text, expected, expected_quote
):
    m = parse_mention(user, database)
    actual = update_quote(is_exec, m, to_update, new_text, database)
    actual_quote = quote_str(quotes_query(to_update, database).one_or_none())

    assert actual == expected
    assert actual_quote == expected_quote


@pytest.mark.parametrize(
    ["is_exec", "user", "target", "expected", "db_size"],
    PURGE_QUOTES.values(),
    ids=PURGE_QUOTES.keys(),
)
def test_purge_quotes(database, is_exec, user, target, expected, db_size):
    u = parse_mention(user, database)
    t = parse_mention(target, database)
    actual = purge_quotes(is_exec, u, t, database)

    assert actual == expected
    assert database.query(Quote).count() == db_size


@pytest.mark.parametrize(
    ["is_exec", "requester", "target", "expected", "try_quote", "oo_size", "q_size"],
    OPTOUTS.values(),
    ids=OPTOUTS.keys(),
)
def test_optout(
    database, is_exec, requester, target, expected, try_quote, oo_size, q_size
):
    if target is None:
        target = requester

    r = parse_mention(requester, database)
    t = parse_mention(target, database)
    actual = opt_out_of_quotes(is_exec, r, t, database)
    actual_from_quote = add_quote(
        requester, t, "quote thingy", datetime.now(), database
    )

    assert actual == expected
    assert database.query(QuoteOptouts).count() == oo_size
    assert actual_from_quote == try_quote
    assert database.query(Quote).count() == q_size


@pytest.mark.parametrize(
    ["requester", "try_quote", "oo_size", "q_size"], OPTINS.values(), ids=OPTINS.keys()
)
def test_optin(database, requester, try_quote, oo_size, q_size):
    r = parse_mention(requester, database)

    opt_in_to_quotes(r, database)
    actual_from_quote = add_quote(
        requester, r, "quote thingy", datetime.now(), database
    )

    assert database.query(QuoteOptouts).count() == oo_size
    assert actual_from_quote == try_quote
    assert database.query(Quote).count() == q_size
