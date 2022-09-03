import logging

from discord.ext import commands
from discord.ext.commands import Bot, CommandError, Context, check
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy_utils import ScalarListException

from models import BlockedKarma, db_session
from utils import get_database_user, is_compsoc_exec_in_guild

LONG_HELP_TEXT = """
Query, display, and modify the blacklisted karma topics.
"""
SHORT_HELP_TEXT = """View and modify the blacklisted karma topics."""


class BlacklistError(CommandError):
    message = None

    def __init__(self, message=None, *args):
        self.message = message
        super().__init__(*args)


class Blacklist(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_group(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def blacklist(self, ctx: Context):
        if not ctx.invoked_subcommand:
            await ctx.send("Subcommand not found")

    @blacklist.command(help="Add a topic to the karma blacklist.")
    @check(is_compsoc_exec_in_guild)
    async def add(self, ctx: Context, item: str):
        author_id = get_database_user(ctx.author).id

        if (
            not db_session.query(BlockedKarma)
            .filter(BlockedKarma.topic == item.casefold())
            .all()
        ):
            blacklist = BlockedKarma(topic=item.casefold(), user_id=author_id)
            db_session.add(blacklist)
            try:
                db_session.commit()
                await ctx.send(f"Added {item} to the karma blacklist. :pencil:")
            except (ScalarListException, SQLAlchemyError) as e:
                db_session.rollback()
                logging.exception(e)
                await ctx.send(
                    f"Something went wrong adding {item} to the karma blacklist. No change has occurred"
                )
        else:
            await ctx.send(
                f"{item} is already in the karma blacklist. :page_with_curl:"
            )

    @blacklist.command(help="Remove a word from the karma blacklist.")
    @check(is_compsoc_exec_in_guild)
    async def remove(self, ctx: Context, item: str):
        if (
            not db_session.query(BlockedKarma)
            .filter(BlockedKarma.topic == item.casefold())
            .all()
        ):
            await ctx.send(f"{item} is not in the karma blacklist. :page_with_curl:")
        else:
            db_session.query(BlockedKarma).filter(
                BlockedKarma.topic == item.casefold()
            ).delete()
            try:
                db_session.commit()
                await ctx.send(
                    f"{item} has been removed from the karma blacklist. :wastebasket:"
                )
            except (ScalarListException, SQLAlchemyError) as e:
                db_session.rollback()
                logging.exception(e)
                await ctx.send(
                    f"Something went wrong removing {item} to the karma blacklist. No change has occurred"
                )

    @blacklist.command(help="List all blacklisted karma topics.")
    @check(is_compsoc_exec_in_guild)
    async def list(self, ctx: Context):
        items = db_session.query(BlockedKarma).all()
        if items:
            list_str = "The topics in the karma blacklist are:\n\n"

            for item in items:
                list_str += f" • **{item.topic}**\n"
        else:
            list_str = "There are no karma topics currently blacklisted! :mag:"

        await ctx.send(list_str)

    @blacklist.command(help="Search for a blacklisted topic.")
    async def search(self, ctx: Context, item: str):
        item_folded = item.replace("*", "%").casefold()
        items = (
            db_session.query(BlockedKarma)
            .filter(BlockedKarma.topic.ilike(f"%{item_folded}%"))
            .all()
        )
        if len(items) == 0:
            await ctx.send(
                f'There were no topics matching "{item}" in the blacklist. :sweat:'
            )
        else:
            if len(items) == 1:
                list_str = f'The topic matching "{item}" in the blacklist is:\n\n'
            else:
                list_str = f'The {"first 10" if len(items) > 10 else ""} topic matching "{item}" in the blacklist are:\n\n'

            # Don't want to spam too much on a search
            max_len = 10
            for it in items:
                if max_len > 0:
                    list_str += f" • **{it.topic}**\n"
                else:
                    break
                max_len -= 1

            await ctx.send(list_str)

    @list.error
    @add.error
    @remove.error
    async def blacklist_error_handler(self, ctx: Context, error: BlacklistError):
        await ctx.send(error.message)


async def setup(bot: Bot):
    await bot.add_cog(Blacklist(bot))
