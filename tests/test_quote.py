import os
from discord.ext.commands.context import Context
from discord.ext.commands.bot import Bot
import pytest
from datetime import datetime

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from config import CONFIG
from cogs.commands.quotes import quotes_query, add_quote, quote_str, delete_quote, update_quote
from models import Base, User, Quote, QuoteOptouts
from utils.mentions import Mention, MentionConverter, MentionType, parse_mention

TEST_QUOTES = [
        Quote(
            author_type="id",
            author_id=1,
            author_string=None,
            quote="talking to myself!",
            created_at=datetime(2018,10,11),
            edited=False,
            edited_at=None,
        ),
        Quote(
            author_type="string",
            author_id=None,
            author_string="ircguy",
            quote="talking to myself! on irc!",
            created_at=datetime(2018,10,12),
            edited=False,
            edited_at=None,
        ),
        Quote(
            author_type="id",
            author_id=2,
            author_string=None,
            quote="talking to someone else!",
            created_at=datetime(2018,10,13),
            edited=False,
            edited_at=None,
        ),
        Quote(
            author_type="string",
            author_id=None,
            author_string="ircguy",
            quote="talking to someone else! on irc!",
            created_at=datetime(2018,10,14),
            edited=False,
            edited_at=None,
        ),
        Quote(
            author_type="id",
            author_id=1,
            author_string=None,
            quote="talking about someone else! from irc!",
            created_at=datetime(2018,10,15),
            edited=False,
            edited_at=None,
        ),
        Quote(
            author_type="string",
            author_id=None,
            author_string="ircguy2",
            quote="something about FOSS idk",
            created_at=datetime(2018,10,16),
            edited=False,
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
    "By ID": (
        "#1",
        [TEST_QUOTES[0]]
    ),
    "By Author (Discord)": (
        "<@!1337>",
        [TEST_QUOTES[2]]
    ),
    "By Author (IRC/String)": (
        "@ircguy",
        [TEST_QUOTES[1],TEST_QUOTES[3]]
    ),
    "By Topic": (
        "irc",
        [TEST_QUOTES[1],TEST_QUOTES[3],TEST_QUOTES[4]]
    ),
    "No valid quotes": (
        "blargleargle",
        []
    )
}

ADD_QUOTES = {
    "Discord user quote": (
        "<@!1000>",
        "Foo said this",
        datetime(1998,12,24),
        "#7",
        "**#7:** \"Foo said this\" - <@1000> (24/12/1998)",
        7
    ),
    "Unregistered user quote":(
        "<@!1034>",
        "Unknown user said this",
        datetime(1998,12,24),
        "#8",
        "**#8:** \"Unknown user said this\" - <@!1034> (24/12/1998)",
        8
    ),
    "IRC user/string quote":(
        "Foobar",
        "Foobar said this",
        datetime(1998,12,24),
        "#9",
        "**#9:** \"Foobar said this\" - Foobar (24/12/1998)",
        9
    )
}

DELETE_QUOTES = {
    "Discord user deleting own quote": (
        False,
        "<@!1000>",
        "#7",
        "Deleted quote with ID #7.",
        8
    ),
    "Discord user deleting someone else's quote": (
        False,
        "<@!1000>",
        "#8",
        "You do not have permission to delete that quote.",
        8
    ),
    "Exec user deleting other quote": (
        True,
        "<@!3001>",
        "#8",
        "Deleted quote with ID #8.",
        7
    ),
    "IRC/String user deleting their quote": (
        False,
        "Foobar",
        "#9",
        "Deleted quote with ID #9.",
        6
    ),
    "Discord user deleting IRC user quote": (
        False,
        "<@!1000>",
        "#2",
        "You do not have permission to delete that quote.",
        6
    ),
    "IRC user deleting Discord user quote": (
        False,
        "ircguy",
        "#1",
        "You do not have permission to delete that quote.",
        6
    ),
    "Delete non-existing quote": (
        False,
        "<@!1000>",
        "#100",
        "No quote with that ID was found.",
        6
    )
}

UPDATE_QUOTES = {
    "Discord user updating their quote": (
        False,
        "<@!1000>",
        "#1",
        "updated quote",
        "Updated quote with ID #1.",
        "**#1:** \"updated quote\" - <@1000> (11/10/2018)"
    ),
    "Discord user updating someone else's quote": (
        False,
        "<@!1000>",
        "#3",
        "updated quote",
        "You do not have permission to update that quote.",
        "**#3:** \"talking to someone else!\" - <@1337> (13/10/2018)"
    ),
    "Exec updating someone else's quote": (
        True,
        "<@!3000>",
        "#3",
        "Exec updated this quote",
        "Updated quote with ID #3.",
        "**#3:** \"Exec updated this quote\" - <@1337> (13/10/2018)"
    ),
    "IRC user updating their quote": (
        False,
        "ircguy",
        "#2",
        "Updated from IRC",
        "Updated quote with ID #2.",
        "**#2:** \"Updated from IRC\" - ircguy (12/10/2018)"
    ),
    "IRC user updating someone else's quote": (
        False,
        "ircguy",
        "#6",
        "Updated from IRC",
        "You do not have permission to update that quote.",
        "**#6:** \"something about FOSS idk\" - ircguy2 (16/10/2018)"
    ),
    "Updating non-existing quote": (
        False,
        "<@!1000>",
        "#100",
        "updating a non-quote",
        "No quote with that ID was found.",
        None
    )
}

@pytest.mark.parametrize(
    ["query","expected"],
    QUERY_QUOTES.values(),
    ids=QUERY_QUOTES.keys()
)
def test_query_quotes(database, query,expected):
    actual = quotes_query(query, database).all()
    assert actual == expected

@pytest.mark.parametrize(
    ["mention","quote","time","new_id","expected","db_size"],
    ADD_QUOTES.values(),
    ids=ADD_QUOTES.keys()
)
def test_add_quotes(database,mention,quote,time,new_id,expected,db_size):
    m = parse_mention(mention,database)
    add_quote(m,quote,time,database)
    q = quotes_query(new_id,database).one_or_none()

    assert quote_str(q) == expected
    assert database.query(Quote).count() == db_size

@pytest.mark.parametrize(
    ["is_exec","user","to_delete","expected","db_size"],
    DELETE_QUOTES.values(),
    ids=DELETE_QUOTES.keys()
)
def test_delete_quotes(database,is_exec,user,to_delete,expected,db_size):
    m = parse_mention(user,database)
    actual = delete_quote(is_exec, m, to_delete,database)
    
    assert actual == expected
    assert database.query(Quote).count() == db_size#

@pytest.mark.parametrize(
    ["is_exec","user","to_update","new_text","expected","expected_quote"],
    UPDATE_QUOTES.values(),
    ids=UPDATE_QUOTES.keys()
)
def test_update_quotes(database,is_exec,user,to_update,new_text,expected,expected_quote):
    m = parse_mention(user,database)
    actual = update_quote(is_exec, m, to_update, new_text, database)
    actual_quote = quote_str(quotes_query(to_update, database).one_or_none())

    assert actual == expected
    assert actual_quote == expected_quote