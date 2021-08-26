from discord.ext.commands.converter import clean_content
from utils.MaybeMention import MaybeMention
from datetime import datetime
import logging

from discord.ext import commands
from discord.ext.commands import Bot, Context
from discord import AllowedMentions
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy_utils import ScalarListException
from sqlalchemy.sql import func

from models import Quote, QuoteOptouts, db_session
from utils import (
    get_database_user,
    get_name_string,
    is_compsoc_exec_in_guild,
    user_is_irc_bot,
)

LONG_HELP_TEXT = """
Pull a random quote. Pull quotes by ID using "#ID", by author using "@username", or by topic by entering plain text
"""
SHORT_HELP_TEXT = """Record and manage quotes attributed to authors"""

def quote_by_id(id):
    if(
        not id or
        id[0] != "#" or
        len(id) < 2 or
        not id[1:].isnumeric()
    ):
        return None
    return (
        db_session.query(Quote)
        .filter(Quote.quote_id == int(id[1:]))
        .first()
    )

#check if user has permissions for this quote
async def has_quote_perms(ctx, quote):
    is_exec = await is_compsoc_exec_in_guild(ctx)
    author_id = get_database_user(ctx.author).id

    return is_exec or author_id  in [quote.author_id, quote.submitter_id]


class Quotes(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group(
        invoke_without_command=True, help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT
    )
    async def quote(self, ctx: Context, argument=None):

        # pick any quote
        if argument is None:
            query = db_session.query(Quote)
        else:
            mention = await MaybeMention.convert(self, ctx, argument)

            if isinstance(mention, str):
                if mention[0] == "#" and mention[1:].isnumeric:
                    query = db_session.query(Quote).filter(
                        Quote.quote_id == int(mention[1:])
                    )
                # pick from string-authors
                elif mention[0] == "@":
                    query = db_session.query(Quote).filter(
                        Quote.author_string == mention[1:]
                    )
                # find specific quote
                # pick from quotes containing the text
                else:
                    query = db_session.query(Quote).filter(
                        Quote.quote.contains(mention)
                    )
            # pick from id-authors
            else:
                query = db_session.query(Quote).filter(Quote.author_id == mention.id)

        # select a random quote if one exists
        q = query.order_by(func.random()).first()

        if q is None:
            message = "Invalid subcommand or no quote matched the criteria"
        else:

            # get quote author
            if q.author_type == "id":
                # note: we pull just the username for now until i can figure out how to display mentions on mobile.
                author = q.author.username
            else:
                author = q.author_string

            date = q.created_at.strftime("%d/%m/%Y")

            # create message
            message = f"**#{q.quote_id}:** \"{q.quote}\" - {author} ({date})"

        # send message with no pings
        await ctx.send(message, allowed_mentions=AllowedMentions().none())

    @quote.command(help="Add a quote, format !quote add <author> \"<quote text>\".")
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
        
        quote = quote_by_id(argument)

        if quote is None:
            await ctx.send("Invalid or missing quote ID.")
            return

        if await has_quote_perms(ctx, quote):
            #delete quote
            db_session.query(Quote).filter(Quote.quote_id == quote.quote_id).delete()
            await ctx.send(f"Deleted quote with ID #{quote.quote_id}.")
        else:
            await ctx.send("You do not have permission to delete that quote.")

    @quote.command(help="Update a quote, format !quote update #ID \"<new text>\".")
    async def update(self, ctx: Context, *args: clean_content):
        if len(args) != 2:
            await ctx.send("Invalid format.")
            return

        quote = quote_by_id(args[0])

        if quote is None:
            await ctx.send("Invalid or missing quote ID.")
            return
        
        if await has_quote_perms(ctx, quote):
            #update quote
            q_update = {
                Quote.quote : args[1],
                Quote.edited : True,
                Quote.edited_at : datetime.now()
            }
            db_session.query(Quote).filter(Quote.quote_id == quote.quote_id).update(q_update)
            await ctx.send(f"Updated quote with ID #{quote.quote_id}.")
        else:
            ctx.send("You do not have permission to update that quote.")

    @quote.command(help="Purge all quotes by an author, format !quote purge <author>. Only exec may purge authors other than themselves.")
    async def purge(self, ctx: Context, target: MaybeMention):
        if isinstance(target, str):
            f = (
                db_session.query(Quote)
                .filter(Quote.author_string == target)
            )
        else:
            f = (
                db_session.query(Quote)
                .filter(Quote.author_id == target.id)
            )
        
        quotes = f.all()
        to_delete = len(quotes)

        if to_delete == 0:
            await ctx.send("Author has no quotes to purge.")
        elif not await has_quote_perms(ctx, quotes[0]):
            await ctx.send("You do not have permission to purge this author.")
        else:
            f.delete()
            await ctx.send(f"Purged {to_delete} quotes from author.")

    @quote.command(help="Opt out of being quoted. Only exec can opt out on behalf of others.")
    async def optout(self, ctx: Context, target: MaybeMention=None):
        user_type = "id"

        # get the author's id/name
        display_name = get_name_string(ctx.message)

        #set self as target if none provided
        if target is None:
            target = await MaybeMention().convert(ctx, ctx.author)

        #get target details and check if we have permission
        if user_is_irc_bot(ctx):
            user_type = "string"
            user_id = None
            user_string = display_name
            
            if user_string != target:
                await ctx.send("You do not have permission to opt-out that user.")
                return
        else:
            author_id = get_database_user(ctx.author).id
            
            if isinstance(target,str):
                if await is_compsoc_exec_in_guild(ctx):
                    user_type = "string"
                    user_id = None
                    user_string = target
                else:
                    await ctx.send("You do not have permission to opt-out that user.")
                    return
            elif author_id == target.id or await is_compsoc_exec_in_guild(ctx):
                user_id = target.id
                user_string = None
            else:
                await ctx.send("You do not have permission to opt-out that user.")
                return

        #check to see if target is opted out already
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

        #opt out
        outpout = QuoteOptouts(
            user_type=user_type,
            user_id=user_id,
            user_string=user_string
        )
        db_session.add(outpout)
        try:
            db_session.commit()
             #purge old quotes
            await Quotes.purge(self, ctx, target)
            await ctx.send(f"User has been opted out of quotes. They may opt in again later with the optin command.")
        except (ScalarListException, SQLAlchemyError) as e:
            db_session.rollback()
            logging.exception(e)
            await ctx.send(f"Something went wrong")



def setup(bot: Bot):
    bot.add_cog(Quotes(bot))
