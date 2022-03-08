import logging
import re
from datetime import datetime
from enum import Enum, auto, unique
from functools import singledispatch
from typing import Optional, Union

from discord import AllowedMentions
from discord.ext import commands
from discord.ext.commands import Bot, Context, Converter
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func
from sqlalchemy_utils import ScalarListException

from models import db_session
from models.quote import Quote, QuoteOptouts
from utils import (
    get_database_user,
    get_name_string,
    is_compsoc_exec_in_guild,
    user_is_irc_bot,
)
from utils.mentions import Mention, MentionConverter, MentionType

LONG_HELP_TEXT = """
Pull a random quote. Pull quotes by ID using "#ID", by author using "@username", or by topic by entering plain text
"""
SHORT_HELP_TEXT = """Record and manage quotes attributed to authors"""

MYSTERY_ERROR = "Magical mystery error! go yell at the tech officer."

MC = MentionConverter()


@unique
class QuoteError(Enum):
    BAD_FORMAT = auto()
    NOT_PERMITTED = auto()
    NOT_FOUND = auto()
    OPTED_OUT = auto()
    DB_ERROR = auto()
    NO_OP = auto()


class QuoteException(Exception):
    def __init__(
        self,
        err: QuoteError,
        msg=None,
    ):
        self.message = msg
        self.err = err


QuoteID = int


class QuoteIDConverter(Converter):
    async def convert(self, ctx, string) -> QuoteID:
        if not re.fullmatch(r"#\d+", string):
            raise QuoteException(QuoteError.BAD_FORMAT)

        return int(string[1:])


def is_id(string: str) -> bool:
    return re.fullmatch(r"#\d+", string) is not None


def user_opted_out(user: Mention, session=db_session) -> bool:
    """check if mentioned user has opted out"""

    if user.is_id_type():
        f = QuoteOptouts.user_id == user.id
    else:
        f = QuoteOptouts.user_string == user.string

    q = session.query(QuoteOptouts).filter(f).one_or_none()

    return q is not None


def ctx_to_mention(ctx):
    """Convert requester name to Mention"""
    if user_is_irc_bot(ctx):
        return Mention.string_mention(get_name_string(ctx))
    else:
        return Mention.id_mention(get_database_user(ctx.author).id)


def has_quote_perms(is_exec, requester: Mention, quote: Quote):
    """check if user has permissions for this quote"""
    if is_exec:
        return True

    if quote.author_type == MentionType.ID:
        return requester.id == quote.author_id

    return requester.string == quote.author_string


def quote_str(q: Quote) -> str:
    """Generate the quote string for posting"""

    date = q.created_at.strftime("%d/%m/%Y")
    return f'**#{q.quote_id}:** "{q.quote}" - {q.author_to_string()} ({date})'


@singledispatch
def quotes_query(query: str, session=db_session):
    """query by topic"""
    return session.query(Quote).filter(Quote.quote.contains(query))


@quotes_query.register
def _(query: QuoteID, session=db_session):
    """query by ID"""
    return session.query(Quote).filter(Quote.quote_id == query)


@quotes_query.register
def _(query: Mention, session=db_session):
    """query by Mention"""
    if query.is_id_type():
        return session.query(Quote).filter(Quote.author_id == query.id)
    else:
        return session.query(Quote).filter(Quote.author_string == query.string)


def add_quote(author: Mention, quote, time, session=db_session) -> str:
    """Add a quote by the specified author"""
    if quote is None:
        raise QuoteException(QuoteError.BAD_FORMAT)

    if user_opted_out(author, session):
        raise QuoteException(QuoteError.OPTED_OUT)

    if author.is_id_type():
        new_quote = Quote.id_quote(author.id, quote, time)
    else:
        new_quote = Quote.string_quote(author.string, quote, time)
    try:
        session.add(new_quote)
        session.commit()
        return str(new_quote.quote_id)
    except (ScalarListException, SQLAlchemyError) as e:
        session.rollback()
        logging.exception(e)
        raise QuoteException(QuoteError.DB_ERROR)


def delete_quote(
    is_exec, requester: Mention, query: QuoteID, session=db_session
) -> str:

    quote = quotes_query(query, session).one_or_none()

    if quote is None:
        raise QuoteException(QuoteError.NOT_FOUND)

    if has_quote_perms(is_exec, requester, quote):
        # delete quote
        try:
            session.delete(quote)
            session.commit()
            return str(query)
        except (ScalarListException, SQLAlchemyError) as e:
            session.rollback()
            logging.exception(e)
            raise QuoteException(QuoteError.DB_ERROR)
    else:
        raise QuoteException(QuoteError.NOT_PERMITTED)


def update_quote(
    is_exec, requester: Mention, quote_id: QuoteID, new_text, session=db_session
) -> str:

    quote = quotes_query(quote_id, session).one_or_none()

    if quote is None:
        raise QuoteException(QuoteError.NOT_FOUND)

    if has_quote_perms(is_exec, requester, quote):
        # update quote
        try:
            quote.quote = new_text
            quote.edited_at = datetime.now()
            session.commit()
            return str(quote_id)
        except (ScalarListException, SQLAlchemyError) as e:
            session.rollback()
            logging.exception(e)
            raise QuoteException(QuoteError.DB_ERROR)
    else:
        raise QuoteException(QuoteError.NOT_PERMITTED)


def purge_quotes(
    is_exec, requester: Mention, target: Mention, session=db_session
) -> str:
    if not is_exec and requester != target:
        raise QuoteException(QuoteError.NOT_PERMITTED)

    # get quotes
    if target.is_id_type():
        f = session.query(Quote).filter(Quote.author_id == target.id)
    else:
        f = session.query(Quote).filter(Quote.author_string == target.string)

    to_delete = f.count()

    try:
        f.delete()
        session.commit()
        return str(to_delete)
    except (ScalarListException, SQLAlchemyError) as e:
        session.rollback()
        logging.exception(e)
        raise QuoteException(QuoteError.DB_ERROR)


def opt_out_of_quotes(
    is_exec, requester: Mention, target: Mention = None, session=db_session
) -> str:
    # if no target, target ourselves
    if target is None:
        target = requester

    # check if requester has permission
    permission = True

    if requester.is_id_type():
        # discord user check (with exec override)
        if requester.id != target.id and not is_exec:
            permission = False
    else:
        if requester.string != target.string and not is_exec:
            permission = False

    if not permission:
        raise QuoteException(QuoteError.NOT_PERMITTED)

    # check if user has opted out
    if target.is_id_type():
        f = QuoteOptouts.user_id == target.id
    else:
        f = QuoteOptouts.user_string == target.string

    q = session.query(QuoteOptouts).filter(f).one_or_none()

    if q is not None:
        raise QuoteException(QuoteError.OPTED_OUT)

    # opt out user
    optout = QuoteOptouts(
        user_type=target.type, user_id=target.id, user_string=target.string
    )
    try:
        session.add(optout)
        session.commit()
        # purge old quotes
        deleted = purge_quotes(is_exec, requester, target, session)
        session.commit()
        return deleted
    except (ScalarListException, SQLAlchemyError) as e:
        session.rollback()
        logging.exception(e)
        raise QuoteException(QuoteError.DB_ERROR)


def opt_in_to_quotes(requester: Mention, session=db_session) -> str:
    # check to see if target is opted out already
    if requester.is_id_type():
        q = session.query(QuoteOptouts).filter(QuoteOptouts.user_id == requester.id)
    else:
        q = session.query(QuoteOptouts).filter(
            QuoteOptouts.user_string == requester.string
        )

    if q.one_or_none() is None:
        raise QuoteException(QuoteError.NO_OP)

    # opt in
    try:
        q.delete()
        session.commit()
        return "OK"
    except (ScalarListException, SQLAlchemyError) as e:
        session.rollback()
        logging.exception(e)
        raise QuoteException(QuoteError.DB_ERROR)


class QueryInputConverter(Converter):
    async def convert(self, ctx, argument) -> Union[Mention, QuoteID, str]:
        if is_id(argument):
            return int(argument[1:])

        if argument[0] == "@":
            return Mention.string_mention(argument[1:])

        argument = await MC.convert(ctx, argument)

        return argument


class Quotes(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group(
        invoke_without_command=True, help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT
    )
    async def quote(self, ctx: Context, *, query_arg: QueryInputConverter = None):
        if query_arg is not None:
            query = quotes_query(query_arg)
        else:
            query = db_session.query(Quote)

        # select a random quote if one exists
        q: Optional[Quote] = query.order_by(func.random()).first()

        if q is None:
            message = "No quote matched the criteria"
        else:
            # create message
            message = quote_str(q)

        # send message with no pings
        await ctx.send(message, allowed_mentions=AllowedMentions().none())

    @quote.command()
    async def add(self, ctx: Context, author: MentionConverter, *, quote):
        """Add a quote, format !quote add <author> <quote text>"""
        requester = get_name_string(ctx)
        now = datetime.now()

        try:
            quote_id = add_quote(author, quote, now)

            result = f"Thank you {requester}, recorded quote with ID #{quote_id}."
        except QuoteException as e:
            if e.err == QuoteError.BAD_FORMAT:
                result = "Invalid format: no quote to record."
            elif e.err == QuoteError.OPTED_OUT:
                result = "Invalid Author: User has opted out of being quoted."
            elif e.err == QuoteError.DB_ERROR:
                result = "Database error."
            else:
                result = MYSTERY_ERROR

        await ctx.send(result)

    @quote.command()
    async def delete(self, ctx: Context, query: QuoteIDConverter):
        """Delete a quote, format !quote delete #ID."""
        requester = ctx_to_mention(ctx)
        is_exec = await is_compsoc_exec_in_guild(ctx)

        try:
            quote_id = delete_quote(is_exec, requester, query)
            result = f"Deleted quote with ID #{quote_id}."
        except QuoteException as e:
            if e.err == QuoteError.BAD_FORMAT:
                result = "Invalid format: provide quote ID."
            elif e.err == QuoteError.NOT_FOUND:
                result = "Invalid ID: no quote found with that ID."
            elif e.err == QuoteError.NOT_PERMITTED:
                result = "You do not have permission to delete this quote."
            elif e.err == QuoteError.DB_ERROR:
                result = "Database error."
            else:
                result = MYSTERY_ERROR

        await ctx.send(result)

    @quote.command()
    async def update(self, ctx: Context, quote_id: QuoteIDConverter, *, argument: str):
        """Update a quote, format !quote update #ID <new text>"""
        is_exec = await is_compsoc_exec_in_guild(ctx)
        requester = ctx_to_mention(ctx)

        try:
            quote_id = update_quote(is_exec, requester, quote_id, argument)
            result = f"Updated quote with ID #{quote_id}."
        except QuoteException as e:
            if e.err == QuoteError.BAD_FORMAT:
                result = "Invalid format: supply a valid ID and update text."
            elif e.err == QuoteError.NOT_FOUND:
                result = "Error: no quote with that ID found."
            elif e.err == QuoteError.NOT_PERMITTED:
                result = "You do not have permission to update this quote."
            elif e.err == QuoteError.DB_ERROR:
                result = "Database error."
            else:
                result = MYSTERY_ERROR

        await ctx.send(result)

    @quote.command()
    async def purge(self, ctx: Context, target: MentionConverter):
        """Purge all quotes by an author, format !quote purge <author>. Only exec may purge authors other than themselves."""
        is_exec = await is_compsoc_exec_in_guild(ctx)
        requester = ctx_to_mention(ctx)

        try:
            purged = purge_quotes(is_exec, requester, target)
            result = f"Deleted {purged} quotes."
        except QuoteException as e:
            if e.err == QuoteError.NOT_PERMITTED:
                result = "You do not have permission to purge these quote."
            elif e.err == QuoteError.DB_ERROR:
                result = "Database error."
            else:
                result = MYSTERY_ERROR

        await ctx.send(result)

    @quote.command()
    async def optout(self, ctx: Context, target: MentionConverter = None):
        """Opt out of being quoted, format !quote optout. Only exec can opt out on behalf of others."""
        is_exec = await is_compsoc_exec_in_guild(ctx)
        requester = ctx_to_mention(ctx)

        try:
            purged = opt_out_of_quotes(is_exec, requester, target)
            result = f"Deleted {purged} quotes.\nUser can opt back in with the !quote optin command."
        except QuoteException as e:
            if e.err == QuoteError.NOT_PERMITTED:
                result = "You do not have permission to opt out this user."
            elif e.err == QuoteError.OPTED_OUT:
                result = "User has already opted out."
            elif e.err == QuoteError.DB_ERROR:
                result = "Database error."
            else:
                result = MYSTERY_ERROR

        await ctx.send(result)

    @quote.command()
    async def optin(self, ctx: Context):
        """Opt in to being quoted if you have previously opted out, format !quote optin."""
        user = ctx_to_mention(ctx)

        try:
            opt_in_to_quotes(user)
            result = "User has opted in to being quoted."
        except QuoteException as e:
            if e.err == QuoteError.NO_OP:
                result = "User has already opted in."
            else:
                result = MYSTERY_ERROR

        await ctx.send(result)


def setup(bot: Bot):
    bot.add_cog(Quotes(bot))
