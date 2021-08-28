import logging
import re
from datetime import datetime
from enum import Enum
from typing import Optional

from discord import AllowedMentions
from discord.ext import commands
from discord.ext.commands import Bot, Context, Converter
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func
from sqlalchemy_utils import ScalarListException

from models import db_session
from models.quote import *
from utils import (
    get_database_user,
    get_name_string,
    is_compsoc_exec_in_guild,
    user_is_irc_bot,
)
from utils.mentions import *

LONG_HELP_TEXT = """
Pull a random quote. Pull quotes by ID using "#ID", by author using "@username", or by topic by entering plain text
"""
SHORT_HELP_TEXT = """Record and manage quotes attributed to authors"""


class QuoteError(Enum):
    BAD_FORMAT = 1
    NOT_PERMITTED = (2,)
    NOT_FOUND = (3,)
    OPTED_OUT = (4,)
    DB_ERROR = (5,)
    NO_OP = 6


class QuoteException(Exception):
    def __init__(
        self,
        err: QuoteError,
        msg=None,
    ):
        self.message = (msg,)
        self.err = err


def is_id(string) -> bool:
    if not isinstance(string, str):
        return False
    return re.fullmatch("#\d+", string) is not None


"""check if mentioned user has opted out"""


def user_opted_out(user: Mention, db_session=db_session) -> bool:
    if user.is_id_type():
        f = QuoteOptouts.user_id == user.id
    else:
        f = QuoteOptouts.user_string == user.string

    q = db_session.query(QuoteOptouts).filter(f).one_or_none()

    return q is not None


def ctx_to_mention(ctx):
    if user_is_irc_bot(ctx):
        return MakeMention.string_mention(get_name_string(ctx))
    else:
        return MakeMention.id_mention(get_database_user(ctx.author).id)


""" check if user has permissions for this quote """


def has_quote_perms(is_exec, requester: Mention, quote: Quote):
    if is_exec:
        return True

    if quote.author_type == MentionType.ID:
        return requester.id == quote.author_id

    return requester.string == quote.author_string


def quote_str(q: Quote) -> Optional[str]:
    if q is None:
        return None
    date = q.created_at.strftime("%d/%m/%Y")
    return f'**#{q.quote_id}:** "{q.quote}" - {q.author_to_string()} ({date})'


def quotes_query(query: Mention, db_session=db_session):
    # by discord user
    if query.is_id_type():
        return db_session.query(Quote).filter(Quote.author_id == query.id)

    # by id
    if is_id(query.string):
        return db_session.query(Quote).filter(Quote.quote_id == int(query.string[1:]))

    # by other author
    if len(query.string) > 1 and query.string[0] == "@":
        return db_session.query(Quote).filter(Quote.author_string == query.string[1:])

    if len(query.string) > 1 and query.string[1] == "@":
        return db_session.query(Quote).filter(Quote.author_string == query.string)

    # by topic
    return db_session.query(Quote).filter(Quote.quote.contains(query.string))


def add_quote(author: Mention, quote, time, db_session=db_session) -> str:
    if quote is None:
        raise QuoteException(QuoteError.BAD_FORMAT)

    if user_opted_out(author, db_session):
        raise QuoteException(QuoteError.OPTED_OUT)

    if author.is_id_type():
        new_quote = MakeQuote.id_quote(author.id, quote, time)
    else:
        new_quote = MakeQuote.string_quote(author.string, quote, time)

    try:
        db_session.add(new_quote)
        db_session.commit()
        return str(new_quote.quote_id)
    except (ScalarListException, SQLAlchemyError) as e:
        db_session.rollback()
        logging.exception(e)
        raise QuoteException(QuoteError.DB_ERROR)


def delete_quote(
    is_exec, requester: Mention, query, db_session=db_session
) -> str:
    if query is None or not is_id(query.string):
        raise QuoteException(QuoteError.BAD_FORMAT)

    quote = quotes_query(query, db_session).one_or_none()

    if quote is None:
        raise QuoteException(QuoteError.NOT_FOUND)

    if has_quote_perms(is_exec, requester, quote):
        # delete quote
        try:
            db_session.delete(quote)
            db_session.commit()
            return query.string
        except (ScalarListException, SQLAlchemyError) as e:
            db_session.rollback()
            logging.exception(e)
            raise QuoteException(QuoteError.DB_ERROR)
    else:
        raise QuoteException(QuoteError.NOT_PERMITTED)


def update_quote(
    is_exec, requester: Mention, quote_id, new_text, db_session=db_session
) -> str:
    if not is_id(quote_id.string) or new_text is None:
        raise QuoteException(QuoteError.BAD_FORMAT)

    quote = quotes_query(quote_id, db_session).one_or_none()

    if quote is None:
        raise QuoteException(QuoteError.NOT_FOUND)

    if has_quote_perms(is_exec, requester, quote):
        # update quote
        try:
            quote.quote = new_text
            quote.edited_at = datetime.now()
            db_session.commit()
            return quote_id.string
        except (ScalarListException, SQLAlchemyError) as e:
            db_session.rollback()
            logging.exception(e)
            raise QuoteException(QuoteError.DB_ERROR)
    else:
        raise QuoteException(QuoteError.NOT_PERMITTED)


def purge_quotes(
    is_exec, requester: Mention, target: Mention, db_session=db_session
) -> str:

    # get quotes
    if target.is_id_type():
        f = db_session.query(Quote).filter(Quote.author_id == target.id)
    else:
        f = db_session.query(Quote).filter(Quote.author_string == target.string)

    quotes = f.all()
    to_delete = f.count()

    if any(not has_quote_perms(is_exec, requester, q) for q in quotes):
        raise QuoteException(QuoteError.NOT_PERMITTED)

    try:
        f.delete()
        db_session.commit()
        return str(to_delete)
    except (ScalarListException, SQLAlchemyError) as e:
        db_session.rollback()
        logging.exception(e)
        raise QuoteException(QuoteError.DB_ERROR)


def opt_out_of_quotes(
    is_exec, requester: Mention, target: Mention = None, db_session=db_session
) -> str:
    # if no target, target ourself
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

    q = db_session.query(QuoteOptouts).filter(f).one_or_none()

    if q is not None:
        raise QuoteException(QuoteError.OPTED_OUT)

    # opt out user
    optout = QuoteOptouts(
        user_type=target.type, user_id=target.id, user_string=target.string
    )
    try:
        db_session.add(optout)
        db_session.commit()
        # purge old quotes
        deleted = purge_quotes(is_exec, requester, target, db_session)
        db_session.commit()
        return deleted
    except (ScalarListException, SQLAlchemyError) as e:
        db_session.rollback()
        logging.exception(e)
        raise QuoteException(QuoteError.DB_ERROR)


def opt_in_to_quotes(requester: Mention, db_session=db_session) -> str:
    # check to see if target is opted out already
    if requester.is_id_type():
        q = db_session.query(QuoteOptouts).filter(QuoteOptouts.user_id == requester.id)
    else:
        q = db_session.query(QuoteOptouts).filter(
            QuoteOptouts.user_string == requester.string
        )

    if q.one_or_none() is None:
        raise QuoteException(QuoteError.NO_OP)

    # opt in
    try:
        q.delete()
        db_session.commit()
        return "OK"
    except (ScalarListException, SQLAlchemyError) as e:
        db_session.rollback()
        logging.exception(e)
        raise QuoteException(QuoteError.DB_ERROR)


class QueryConverter(Converter):
    async def convert(self,ctx, argument):
        query = await MentionConverter.convert(ctx,argument)
        return quotes_query(query)


class Quotes(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group(
        invoke_without_command=True, help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT
    )
    async def quote(self, ctx: Context, *, arg: MentionConverter=None):

        if arg is not None:
            query = quotes_query(arg)
        else:
            query = db_session.query(Quote)

        # select a random quote if one exists
        q: Quote = query.order_by(func.random()).first()

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
            result = f"Thank you {requester}, recorded quote with ID #{add_quote(author, quote, now)}."
        except QuoteException as e:
            if e.err == QuoteError.BAD_FORMAT:
                result = "Invalid format: no quote to record."
            elif e.err == QuoteError.OPTED_OUT:
                result = "Invalid Author: User has opted out of being quoted."
            elif e.err == QuoteError.DB_ERROR:
                result = "Database error."

        await ctx.send(result)

    @quote.command()
    async def delete(self, ctx: Context, query:MentionConverter):
        """Delete a quote, format !quote delete #ID."""
        requester = ctx_to_mention(ctx)
        is_exec = await is_compsoc_exec_in_guild(ctx)

        try:
            result = f"Deleted quote with ID {delete_quote(is_exec, requester, query)}."
        except QuoteException as e:
            if e.err == QuoteError.BAD_FORMAT:
                result = "Invalid format: provide quote ID."
            elif e.err == QuoteError.NOT_FOUND:
                result = "Invalid ID: no quote found with that ID."
            elif e.err == QuoteError.NOT_PERMITTED:
                result = "You do not have permission to delete this quote."
            elif e.err == QuoteError.DB_ERROR:
                result = "Database error."

        await ctx.send(result)

    @quote.command()
    async def update(self, ctx: Context, quote_id:MentionConverter, *, argument):
        """Update a quote, format !quote update #ID <new text>"""
        is_exec = await is_compsoc_exec_in_guild(ctx)
        requester = ctx_to_mention(ctx)

        try:
            result = f"Updated quote with ID {update_quote(is_exec, requester, quote_id, argument)}."
        except QuoteException as e:
            if e.err == QuoteError.BAD_FORMAT:
                result = "Invalid format: supply a valid ID and update text."
            elif e.err == QuoteError.NOT_FOUND:
                result = "Error: no quote with that ID found."
            elif e.err == QuoteError.NOT_PERMITTED:
                result = "You do not have permission to update this quote."
            elif e.err == QuoteError.DB_ERROR:
                result = "Database error."

        await ctx.send(result)

    @quote.command()
    async def purge(self, ctx: Context, target: MentionConverter):
        """Purge all quotes by an author, format !quote purge <author>. Only exec may purge authors other than themselves."""
        is_exec = await is_compsoc_exec_in_guild(ctx)
        requester = ctx_to_mention(ctx)

        try:
            result = f"Deleted {purge_quotes(is_exec, requester, target)} quotes."
        except QuoteException as e:
            if e.err == QuoteError.NOT_PERMITTED:
                result = "You do not have permission to purge these quote."
            elif e.err == QuoteError.DB_ERROR:
                result = "Database error."

        await ctx.send(result)

    @quote.command()
    async def optout(self, ctx: Context, target: MentionConverter = None):
        """Opt out of being quoted, format !quote optout. Only exec can opt out on behalf of others."""
        is_exec = await is_compsoc_exec_in_guild(ctx)
        requester = ctx_to_mention(ctx)

        try:
            result = f"Deleted {opt_out_of_quotes(is_exec, requester, target)} quotes.\nUser can opt back in with the !quote optin command."
        except QuoteException as e:
            if e.err == QuoteError.NOT_PERMITTED:
                result = "You do not have permission to opt out this user."
            elif e.err == QuoteError.OPTED_OUT:
                result = "User has already opted out."
            elif e.err == QuoteError.DB_ERROR:
                result = "Database error."

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
                resul = "User has already opted in."

        await ctx.send(result)


def setup(bot: Bot):
    bot.add_cog(Quotes(bot))
