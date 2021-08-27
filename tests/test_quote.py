import os
from discord.ext.commands.context import Context
import pytest
from datetime import datetime

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cogs.commands.quotes import quotes_query, add_quote, quote_str
from models import Base, User, Quote, QuoteOptouts
from utils.mentions import Mention, MentionConverter, MentionType, parse_mention



TEST_QUOTES = [
        Quote(
            author_type="id",
            author_id=1,
            author_string=None,
            quote="talking to myself!",
            created_at=datetime.now(),
            edited=False,
            edited_at=None,
        ),
        Quote(
            author_type="string",
            author_id=None,
            author_string="ircguy",
            quote="talking to myself! on irc!",
            created_at=datetime.now(),
            edited=False,
            edited_at=None,
        ),
        Quote(
            author_type="id",
            author_id=2,
            author_string=None,
            quote="talking to someone else!",
            created_at=datetime.now(),
            edited=False,
            edited_at=None,
        ),
        Quote(
            author_type="string",
            author_id=None,
            author_string="ircguy",
            quote="talking to someone else! on irc!",
            created_at=datetime.now(),
            edited=False,
            edited_at=None,
        ),
        Quote(
            author_type="id",
            author_id=1,
            author_string=None,
            quote="talking about someone else! from irc!",
            created_at=datetime.now(),
            edited=False,
            edited_at=None,
        ),
        Quote(
            author_type="string",
            author_id=None,
            author_string="ircguy2",
            quote="something about FOSS idk",
            created_at=datetime.now(),
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
    "Discord user adding a quote": (
        Mention(MentionType.ID,1,None),
        "Foo said this",
        datetime(2000,10,10),
        "#7",
        "**#7:** \"Foo said this\" - <@1000> (10/10/2000)"
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
    ["mention","quote","time","new_id","expected"],
    ADD_QUOTES.values(),
    ids=ADD_QUOTES.keys()
)
def test_add_quotes(database,mention,quote,time,new_id,expected):
    add_quote(mention,quote,time,database)
    q = quotes_query(new_id,database).first()

    assert quote_str(q) == expected