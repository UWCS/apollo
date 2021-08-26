from utils.MaybeMention import MaybeMention
from models.user import User
from datetime import datetime
import logging
from random import choice

from discord.ext import commands
from discord.ext.commands import Bot, Context
from discord import AllowedMentions
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy_utils import ScalarListException
from sqlalchemy.sql import func

from models import Quote, db_session
from utils import (
    get_database_user,
    get_database_user_from_id,
    get_name_string,
    user_is_irc_bot,
)

LONG_HELP_TEXT = """
Pull a random quote. Pull quotes by ID using "#ID", by author using "@username", or by topic by entering plain text
"""
SHORT_HELP_TEXT = """Record and manage quotes attributed to authors"""


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
            message = f"#{q.quote_id}: {q.quote} - {author} ({date})"

        # send message with no pings
        await ctx.send(message, allowed_mentions=AllowedMentions().none())

    @quote.command(help="Add a quote, format !quote add <author> <quote text>.")
    async def add(self, ctx: Context, author: MaybeMention, *, quote_text: str):
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
            quote=quote_text,
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


def setup(bot: Bot):
    bot.add_cog(Quotes(bot))
