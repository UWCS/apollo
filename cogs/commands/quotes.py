import logging
import re
from datetime import datetime
from typing import List, Optional

from discord import AllowedMentions
from discord.ext import commands
from discord.ext.commands import Bot, Context, Converter
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func
from sqlalchemy_utils import ScalarListException

from models import Quote, QuoteOptouts, db_session
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


def is_id(string) -> bool:
    if not isinstance(string, str):
        return False
    return re.fullmatch("#\d+", string) is not None


"""check if mentioned user has opted out"""
def user_opted_out(user: Mention, db_session=db_session):
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


def quotes_query(query, db_session=db_session):
    res = parse_mention(query, db_session)

    # by discord user
    if res.is_id_type():
        return db_session.query(Quote).filter(Quote.author_id == res.id)

    # by id
    if is_id(res.string):
        return db_session.query(Quote).filter(Quote.quote_id == int(res.string[1:]))

    # by other author
    if res.string[0] == "@" and len(res.string) > 1:
        return db_session.query(Quote).filter(Quote.author_string == res.string[1:])

    # by topic
    return db_session.query(Quote).filter(Quote.quote.contains(res.string))


def add_quote(requester, author: Mention, quote, time, db_session=db_session) -> str:
    if quote is None:
        return "Invalid format."

    if user_opted_out(author, db_session):
        return "User has opted out of being quoted."

    new_quote = Quote(
        author_type=author.type,
        author_id=author.id,
        author_string=author.string,
        quote=quote,
        created_at=time,
        edited_at=None,
    )

    try:
        db_session.add(new_quote)
        db_session.commit()
        return f"Thanks {requester}, I have saved this quote with the ID #{new_quote.quote_id}."
    except (ScalarListException, SQLAlchemyError) as e:
        db_session.rollback()
        logging.exception(e)
        return "Something went wrong"


def delete_quote(is_exec, requester: Mention, argument, db_session=db_session) -> str:
    if argument is None or not is_id(argument):
        return "Invalid quote ID."

    quote = quotes_query(argument, db_session).one_or_none()

    if quote is None:
        return "No quote with that ID was found."

    if has_quote_perms(is_exec, requester, quote):
        # delete quote
        try:
            db_session.delete(quote)
            db_session.commit()
            return f"Deleted quote with ID {argument}."
        except (ScalarListException, SQLAlchemyError) as e:
            db_session.rollback()
            logging.exception(e)
            return f"Something went wrong"
    else:
        return "You do not have permission to delete that quote."


def update_quote(
    is_exec, requester: Mention, quote_id, new_text, db_session=db_session
) -> str:
    if not is_id(quote_id):
        return "Invalid quote ID."

    if new_text is None:
        return "Invalid format."

    quote = quotes_query(quote_id, db_session).one_or_none()

    if quote is None:
        return "No quote with that ID was found."

    if has_quote_perms(is_exec, requester, quote):
        # update quote
        try:
            quote.quote = new_text
            quote.edited_at = datetime.now()
            db_session.commit()
            return f"Updated quote with ID {quote_id}."
        except (ScalarListException, SQLAlchemyError) as e:
            db_session.rollback()
            logging.exception(e)
            return f"Something went wrong"
    else:
        return "You do not have permission to update that quote."


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

    if to_delete == 0:
        return "Author has no quotes to purge."

    if not any(has_quote_perms(is_exec, requester, q) for q in quotes):
        return "You do not have permission to purge this author."

    try:
        f.delete()
        db_session.commit()
        return f"Purged {to_delete} quotes from author."
    except (ScalarListException, SQLAlchemyError) as e:
        db_session.rollback()
        logging.exception(e)
        return f"Something went wrong"


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
        return "You do not have permission to opt-out that user."

    # check if user has opted out
    if target.is_id_type():
        f = QuoteOptouts.user_id == target.id
    else:
        f = QuoteOptouts.user_string == target.string

    q = db_session.query(QuoteOptouts).filter(f).one_or_none()

    if q is not None:
        return "User has already opted out."

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
        return f"{deleted}\nUser has been opted out of quotes. They may opt in again later with the optin command."
    except (ScalarListException, SQLAlchemyError) as e:
        db_session.rollback()
        logging.exception(e)
        return "Something went wrong"


def opt_in_to_quotes(requester: Mention, db_session=db_session) -> str:
    # check to see if target is opted out already
    if requester.is_id_type():
        q = db_session.query(QuoteOptouts).filter(QuoteOptouts.user_id == requester.id)
    else:
        q = db_session.query(QuoteOptouts).filter(
            QuoteOptouts.user_string == requester.string
        )

    if q.one_or_none() is None:
        return "User is already opted in."

    # opt in
    try:
        q.delete()
        db_session.commit()
        return "User has opted in to being quoted."
    except (ScalarListException, SQLAlchemyError) as e:
        db_session.rollback()
        logging.exception(e)
        return "Something went wrong"


class QueryConverter(Converter):
    async def convert(self, ctx, argument):
        return quotes_query(argument)


class Quotes(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group(
        invoke_without_command=True, help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT
    )
    async def quote(self, ctx: Context, arg: QueryConverter = None):
        query = arg or db_session.query(Quote)

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
        result = add_quote(requester, author, quote, now)
        await ctx.send(result)

    @quote.command()
    async def delete(self, ctx: Context, argument):
        """Delete a quote, format !quote delete #ID."""
        requester = ctx_to_mention(ctx)
        is_exec = await is_compsoc_exec_in_guild(ctx)
        result = delete_quote(is_exec, requester, argument)
        await ctx.send(result)

    @quote.command()
    async def update(self, ctx: Context, quote_id, *, argument):
        """Update a quote, format !quote update #ID <new text>"""
        is_exec = await is_compsoc_exec_in_guild(ctx)
        requester = ctx_to_mention(ctx)
        result = update_quote(is_exec, requester, quote_id, argument)
        await ctx.send(result)

    @quote.command()
    async def purge(self, ctx: Context, target: MentionConverter):
        """Purge all quotes by an author, format !quote purge <author>. Only exec may purge authors other than themselves."""
        is_exec = await is_compsoc_exec_in_guild(ctx)
        requester = ctx_to_mention(ctx)
        result = purge_quotes(is_exec, requester, target)
        await ctx.send(result)

    @quote.command()
    async def optout(
        self, ctx: Context, target: MentionConverter = None
    ):
        """Opt out of being quoted, format !quote optout. Only exec can opt out on behalf of others."""
        is_exec = await is_compsoc_exec_in_guild(ctx)
        requester = ctx_to_mention(ctx)
        result = opt_out_of_quotes(is_exec, requester, target)
        await ctx.send(result)

    @quote.command()
    async def optin(self, ctx: Context):
        """Opt in to being quoted if you have previously opted out, format !quote optin."""
        user = ctx_to_mention(ctx)
        result = opt_in_to_quotes(user)
        await ctx.send(result)


def setup(bot: Bot):
    bot.add_cog(Quotes(bot))
