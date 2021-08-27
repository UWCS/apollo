import logging
import re
from datetime import datetime
from typing import Optional

from discord import AllowedMentions
from discord.ext import commands
from discord.ext.commands import Bot, Context, Converter
from discord.ext.commands.converter import clean_content
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func
from sqlalchemy.sql.selectable import CompoundSelect
from sqlalchemy_utils import ScalarListException

from models import User, Quote, QuoteOptouts, db_session
from utils import (
    get_database_user,
    get_name_string,
    is_compsoc_exec_in_guild,
    user_is_irc_bot,
)
from utils.mentions import MentionConverter

LONG_HELP_TEXT = """
Pull a random quote. Pull quotes by ID using "#ID", by author using "@username", or by topic by entering plain text
"""
SHORT_HELP_TEXT = """Record and manage quotes attributed to authors"""

def is_id(string) -> bool:
    return re.match("^#\d+$",string)

class QuoteQuery(Converter):
    async def convert(self,ctx, argument):
        #by id
        if is_id(argument):
            return db_session.query(Quote).filter(Quote.quote_id == int(argument[1:]))
        
        res = await MaybeMention.convert(self,ctx, argument)

        #by author id
        if isinstance(res, User):
            return db_session.query(Quote).filter(Quote.author_id == res.id)
        
        #by author string
        if res[0] == "@" and len(res) > 1:
            return db_session.query(Quote).filter(Quote.author_string == res[1:])

        #by topic
        return db_session.query(Quote).filter(Quote.quote.contains(res))

# check if user has permissions for this quote
async def has_quote_perms(ctx, quote):
    is_exec = await is_compsoc_exec_in_guild(ctx)
    author_id = get_database_user(ctx.author).id

    return is_exec or author_id in [quote.author_id, quote.submitter_id]


class Quotes(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group(
        invoke_without_command=True, help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT
    )
    async def quote(self, ctx: Context, arg: QuoteQuery=None):
        query = arg or db_session.query(Quote)

        # select a random quote if one exists
        q : Quote = query.order_by(func.random()).first()

        if q is None:
            message = "No quote matched the criteria"
        else:
            date = q.created_at.strftime("%d/%m/%Y")

            # create message
            message = f'**#{q.quote_id}:** "{q.quote}" - {q.author_to_string()} ({date})'

        # send message with no pings
        await ctx.send(message, allowed_mentions=AllowedMentions().none())

    @quote.command(help='Add a quote, format !quote add <author> "<quote text>".')
    async def add(self, ctx: Context, author: MaybeMention, *args: clean_content):
        if len(args) != 1:
            await ctx.send("Invalid format.")
            return

        submitter_type = "id"
        author_type = "id"
        now = datetime.now()

        # get the submitter's id/name
        display_name = get_name_string(ctx.message)

        if user_is_irc_bot(ctx):
            submitter_type = "string"
            submitter_id = None
            submitter_string = display_name
        else:
            submitter_id = get_database_user(ctx.author).id
            submitter_string = None

        # get the mentioned user's id/name
        if isinstance(author, str):
            author_type = "string"
            author_id = None
            author_string = author
        else:
            author_id = author.id
            author_string = None

        # check if mentioned user has opted out
        if author_type == "id":
            q = (
                db_session.query(QuoteOptouts)
                .filter(QuoteOptouts.user_id == author_id)
                .count()
            )
        else:
            q = (
                db_session.query(QuoteOptouts)
                .filter(QuoteOptouts.user_string == author_string)
                .count()
            )

        if q != 0:
            await ctx.send("User has opted out of being quoted.")
            return

        new_quote = Quote(
            submitter_type=submitter_type,
            submitter_id=submitter_id,
            submitter_string=submitter_string,
            author_type=author_type,
            author_id=author_id,
            author_string=author_string,
            quote=args[0],
            created_at=now,
            edited=False,
            edited_at=None,
        )
        db_session.add(new_quote)
        try:
            db_session.commit()
            await ctx.send(
                f"Thanks {display_name}, I have saved this quote with the ID {new_quote.quote_id}."
            )
        except (ScalarListException, SQLAlchemyError) as e:
            db_session.rollback()
            logging.exception(e)
            await ctx.send(f"Something went wrong")

    @quote.command(help="Delete a quote, format !quote delete #ID.")
    async def delete(self, ctx: Context, argument=None):

        if argument is None or not is_id(argument):
            await ctx.send("Invalid quote ID.")
            return

        quote = await QuoteQuery.convert(self,ctx,argument)

        if quote.first() is None:
            await ctx.send("No quote with that ID was found.")
            return

        if await has_quote_perms(ctx, quote):
            # delete quote
            try:
                quote.delete()
                db_session.commit()
                await ctx.send(f"Deleted quote with ID {argument}.")
            except (ScalarListException, SQLAlchemyError) as e:
                db_session.rollback()
                logging.exception(e)
                await ctx.send(f"Something went wrong")
        else:
            await ctx.send("You do not have permission to delete that quote.")

    @quote.command(help='Update a quote, format !quote update #ID "<new text>".')
    async def update(self, ctx: Context, *args: clean_content):       
        if len(args) != 2:
            await ctx.send("Invalid format.")
            return

        if not is_id(args[0]):
            await ctx.send("Invalid or missing quote ID.")
            return

        quote = await QuoteQuery.convert(self, ctx, args[0])

        if await has_quote_perms(ctx, quote.first()):
            # update quote
            quote.update({
                Quote.quote: args[1],
                Quote.edited: True,
                Quote.edited_at: datetime.now(),
            })
            await ctx.send(f"Updated quote with ID {args[0]}.")
        else:
            ctx.send("You do not have permission to update that quote.")

    @quote.command(
        help="Purge all quotes by an author, format !quote purge <author>. Only exec may purge authors other than themselves."
    )
    async def purge(self, ctx: Context, target: MaybeMention):
        #get quotes
        if isinstance(target, str):
            f = db_session.query(Quote).filter(Quote.author_string == target)
        else:
            f = db_session.query(Quote).filter(Quote.author_id == target.id)

        quotes = f.all()
        to_delete = len(quotes)

        if to_delete == 0:
            await ctx.send("Author has no quotes to purge.")
        elif not await has_quote_perms(ctx, quotes[0]):
            await ctx.send("You do not have permission to purge this author.")
        else:
            f.delete()
            await ctx.send(f"Purged {to_delete} quotes from author.")

    @quote.command(
        help="Opt out of being quoted, format !quote optout. Only exec can opt out on behalf of others."
    )
    async def optout(self, ctx: Context, target: MaybeMention = None):
        user_type = "id"

        # get the author's id/name
        display_name = get_name_string(ctx.message)

        # get target details and check if we have permission
        if user_is_irc_bot(ctx):
            user_type = "string"
            user_id = None
            user_string = display_name

            if target is not None and user_string != target:
                await ctx.send("You do not have permission to opt-out that user.")
                return
        else:
            author_id = get_database_user(ctx.author).id

            # opt out a user by string
            if isinstance(target, str):
                if await is_compsoc_exec_in_guild(ctx):
                    user_type = "string"
                    user_id = None
                    user_string = target
                else:
                    await ctx.send("You do not have permission to opt-out that user.")
                    return
            # opt out ourself
            elif target is None:
                target = ctx.author
                user_id = author_id
                user_string = None
            # opt out a different user
            elif await is_compsoc_exec_in_guild(ctx):
                user_id = target.id
                user_string = None
            else:
                await ctx.send("You do not have permission to opt-out that user.")
                return
        

        # check to see if target is opted out already
        if user_type == "id":
            q = (
                db_session.query(QuoteOptouts)
                .filter(QuoteOptouts.user_id == user_id)
                .count()
            )
        else:
            q = (
                db_session.query(QuoteOptouts)
                .filter(QuoteOptouts.user_string == user_string)
                .count()
            )
        if q != 0:
            await ctx.send("User has already opted out.")
            return

        # opt out
        outpout = QuoteOptouts(
            user_type=user_type, user_id=user_id, user_string=user_string
        )
        db_session.add(outpout)
        try:
            db_session.commit()
            # purge old quotes
            await Quotes.purge(self, ctx, target)
            await ctx.send(
                f"User has been opted out of quotes. They may opt in again later with the optin command."
            )
        except (ScalarListException, SQLAlchemyError) as e:
            db_session.rollback()
            logging.exception(e)
            await ctx.send(f"Something went wrong")

    @quote.command(
        help="Opt in to being quoted if you have previously opted out, format !quote optin."
    )
    async def optin(self, ctx: Context):
        user_type = "id"

        if user_is_irc_bot(ctx):
            user_type = "string"
            user_id = None
            user_string = get_name_string(ctx.message)
        else:
            user_id = get_database_user(ctx.author).id
            submitter_string = None

        # check to see if target is opted out already
        if user_type == "id":
            q = db_session.query(QuoteOptouts).filter(QuoteOptouts.user_id == user_id)
        else:
            q = db_session.query(QuoteOptouts).filter(
                QuoteOptouts.user_string == user_string
            )
        if q.first() is None:
            await ctx.send("User is already opted in.")
            return

        try:
            q.delete()
            await ctx.send(f"User has opted in to being quoted.")
        except (ScalarListException, SQLAlchemyError) as e:
            db_session.rollback()
            logging.exception(e)
            await ctx.send(f"Something went wrong")


def setup(bot: Bot):
    bot.add_cog(Quotes(bot))