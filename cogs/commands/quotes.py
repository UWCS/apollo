import logging
import re
from datetime import datetime
from typing import List

from discord import AllowedMentions
from discord.ext import commands
from discord.ext.commands import Bot, Context, Converter
from discord.ext.commands.converter import clean_content
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func
from sqlalchemy_utils import ScalarListException

from models import Quote, QuoteOptouts, db_session, quote
from utils import (
    get_database_user,
    get_name_string,
    is_compsoc_exec_in_guild,
    user_is_irc_bot,
)
from utils.mentions import Mention, MentionConverter, MentionType, parse_mention

LONG_HELP_TEXT = """
Pull a random quote. Pull quotes by ID using "#ID", by author using "@username", or by topic by entering plain text
"""
SHORT_HELP_TEXT = """Record and manage quotes attributed to authors"""


def is_id(string) -> bool:
    return re.match("^#\d+$", string)

def user_opted_out(user: Mention):
    # check if mentioned user has opted out
    if user.is_id_type():
        q = (
            db_session.query(QuoteOptouts)
            .filter(QuoteOptouts.user_id == user.id)
            .count()
        )
    else:
        q = (
            db_session.query(QuoteOptouts)
            .filter(QuoteOptouts.user_string == user.string)
            .count()
        )

    return q != 0

def ctx_to_mention(ctx):
    if user_is_irc_bot(ctx):
        return Mention(MentionType.STRING,None,get_name_string(ctx))
    else:
        return Mention(MentionType.ID,get_database_user(ctx.author).id,None)


# check if user has permissions for this quote
def has_quote_perms(is_exec, requester: Mention, quote:Quote):
    if is_exec:
        return True

    if quote.author_type == "id":
        return requester.id == quote.author_id
    
    return requester.string == quote.author_string

def quote_str(q:Quote) -> str:
    if q is None:
        return None
    date = q.created_at.strftime("%d/%m/%Y") 
    return f'**#{q.quote_id}:** "{q.quote}" - {q.author_to_string()} ({date})'

def quotes_query(query, db_session = db_session):
    res = parse_mention(query, db_session)

    # by discord user
    if res.is_id_type():
        return db_session.query(Quote).filter(Quote.author_id == res.id)

    # by id
    if is_id(query):
        return db_session.query(Quote).filter(Quote.quote_id == int(query[1:]))

    # by other author
    if query[0] == "@" and len(query) > 1:
        return db_session.query(Quote).filter(Quote.author_string == query[1:])

    # by topic
    return db_session.query(Quote).filter(Quote.quote.contains(query))

def add_quote(author: Mention, quote, time, db_session = db_session) -> Quote:
    new_quote = Quote(
        author_type=author.type_str(),
        author_id=author.id,
        author_string=author.string,
        quote=quote,
        created_at=time,
        edited=False,
        edited_at=None,
    )
    db_session.add(new_quote)
    db_session.commit()
    
    return new_quote

def delete_quote(is_exec, requester: Mention, argument, db_session = db_session) -> str:
    if argument is None or not is_id(argument):
        return "Invalid quote ID."

    quote = quotes_query(argument,db_session)

    if quote.one_or_none() is None:
        return "No quote with that ID was found."

    if has_quote_perms(is_exec, requester, quote.first()):
        # delete quote
        try:
            quote.delete()
            db_session.commit()
            return f"Deleted quote with ID {argument}."
        except (ScalarListException, SQLAlchemyError) as e:
            db_session.rollback()
            logging.exception(e)
            return f"Something went wrong"
    else:
        return "You do not have permission to delete that quote."

def update_quote(is_exec, requester: Mention, quote_id, new_text, db_session = db_session) -> str:
    if not is_id(quote_id):
        return "Invalid quote ID."
    
    if new_text is None:
        return "Invalid format."

    quote = quotes_query(quote_id, db_session)

    if quote.one_or_none() is None:
        return "No quote with that ID was found."
    
    if has_quote_perms(is_exec, requester, quote.one_or_none()):
        # update quote
        try:
            quote.update(
                {
                    Quote.quote: new_text,
                    Quote.edited: True,
                    Quote.edited_at: datetime.now(),
                }
            )
            db_session.commit()
            return f"Updated quote with ID {quote_id}."
        except (ScalarListException, SQLAlchemyError) as e:
            db_session.rollback()
            logging.exception(e)
            return f"Something went wrong"
    else:
        return "You do not have permission to update that quote."

def purge_quotes(is_exec, requester: Mention, target: Mention, db_session = db_session) -> str:
    # get quotes
    if target.is_id_type():
        f = db_session.query(Quote).filter(Quote.author_id == target.id)
    else:
        f = db_session.query(Quote).filter(Quote.author_string == target.string)

    quotes = f.all()
    to_delete = len(quotes)

    if to_delete == 0:
        return "Author has no quotes to purge."

    if not any([has_quote_perms(is_exec, requester, q) for q in quotes]):
        return "You do not have permission to purge this author."

    try:
        f.delete()
        db_session.commit()
        return f"Purged {to_delete} quotes from author."
    except (ScalarListException, SQLAlchemyError) as e:
        db_session.rollback()
        logging.exception(e)
        return f"Something went wrong"


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

    @quote.command(help='Add a quote, format !quote add <author> "<quote text>".')
    async def add(
        self, ctx: Context, author: MentionConverter, *args: clean_content
    ):
        now = datetime.now()

        if len(args) != 1:
            await ctx.send("Invalid format.")
            return

        if user_opted_out(author):
            await ctx.send("User has opted out of being quoted.")
            return

        try:
            new_quote = add_quote(author, args[0], now)
            await ctx.send(
                f"Thanks {get_name_string(ctx.message)}, I have saved this quote with the ID {new_quote.quote_id}."
            )
        except (ScalarListException, SQLAlchemyError) as e:
            db_session.rollback()
            logging.exception(e)
            await ctx.send(f"Something went wrong")

    @quote.command(help="Delete a quote, format !quote delete #ID.")
    async def delete(self, ctx: Context, argument=None):
        requester = ctx_to_mention(ctx)
        is_exec = await is_compsoc_exec_in_guild(ctx)

        result = delete_quote(is_exec,requester,argument)
        await ctx.send(result)

    @quote.command(help='Update a quote, format !quote update #ID "<new text>".')
    async def update(self, ctx: Context, quote_id, argument=None) -> Quote:
        is_exec = await is_compsoc_exec_in_guild(ctx)

        requester = ctx_to_mention(ctx)

        result = update_quote(is_exec, requester, quote_id, argument)

        await ctx.send(result)

    @quote.command(
        help="Purge all quotes by an author, format !quote purge <author>. Only exec may purge authors other than themselves."
    )
    async def purge(self, ctx: Context, target: MentionConverter) -> List[Quote]:
        is_exec = await is_compsoc_exec_in_guild(ctx)

        requester = ctx_to_mention(ctx)

        result = purge_quotes(is_exec, requester, target)

        await ctx.send(result)

    @quote.command(
        help="Opt out of being quoted, format !quote optout. Only exec can opt out on behalf of others."
    )
    async def optout(
        self, ctx: Context, target: MentionConverter = None
    ) -> QuoteOptouts:
        # get the author's id/name
        display_name = get_name_string(ctx.message)

        # get target details and check if we have permission
        if user_is_irc_bot(ctx):
            user = Mention(MentionType.STRING, None, display_name)

            if target is not None and user.string != target.string:
                target = None
        else:
            requester_id = get_database_user(ctx.author).id

            # opt out ourself
            if target is None:
                target = Mention(MentionType.ID, requester_id, None)
            # opt out a different user
            else:
                if not await is_compsoc_exec_in_guild(ctx):
                    target = None

        if target is None:
            await ctx.send("You do not have permission to opt-out that user.")
            return None

        # check to see if target is opted out already
        if target.is_id_type():
            q = (
                db_session.query(QuoteOptouts)
                .filter(QuoteOptouts.user_id == target.id)
                .count()
            )
        else:
            q = (
                db_session.query(QuoteOptouts)
                .filter(QuoteOptouts.user_string == target.string)
                .count()
            )
        if q != 0:
            await ctx.send("User has already opted out.")
            return None

        # opt out
        outpout = QuoteOptouts(
            user_type=target.type_str(), user_id=target.id, user_string=target.string
        )
        db_session.add(outpout)
        try:
            db_session.commit()
            # purge old quotes
            await Quotes.purge(self, ctx, target)
            await ctx.send(
                f"User has been opted out of quotes. They may opt in again later with the optin command."
            )
            return outpout
        except (ScalarListException, SQLAlchemyError) as e:
            db_session.rollback()
            logging.exception(e)
            await ctx.send(f"Something went wrong")
            return None

    @quote.command(
        help="Opt in to being quoted if you have previously opted out, format !quote optin."
    )
    async def optin(self, ctx: Context) -> QuoteOptouts:

        if user_is_irc_bot(ctx):
            user = Mention(MentionType.STRING, None, get_name_string(ctx.message))
        else:
            user = Mention(MentionType.ID, get_database_user(ctx.author).id, None)

        # check to see if target is opted out already
        if user.is_id_type():
            q = db_session.query(QuoteOptouts).filter(QuoteOptouts.user_id == user.id)
        else:
            q = db_session.query(QuoteOptouts).filter(
                QuoteOptouts.user_string == user.string
            )
        if q.first() is None:
            await ctx.send("User is already opted in.")
            return None

        deleted_record = q.first()

        try:
            q.delete()
            await ctx.send(f"User has opted in to being quoted.")
            return deleted_record
        except (ScalarListException, SQLAlchemyError) as e:
            db_session.rollback()
            logging.exception(e)
            await ctx.send(f"Something went wrong")
            return None


def setup(bot: Bot):
    bot.add_cog(Quotes(bot))
