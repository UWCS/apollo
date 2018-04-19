import discord
from discord.ext import commands
from discord.ext.commands import Context, Bot, CommandError, check

from config import CONFIG
from models import db_session, BlockedKarma, User

LONG_HELP_TEXT = """
Query, display, and modify the blacklisted karma topics.
"""
SHORT_HELP_TEXT = """View and modify the blacklisted karma topics."""


class BlacklistError(CommandError):
    message = None

    def __init__(self, message=None, *args):
        self.message = message
        super().__init__(*args)


def is_compsoc_exec():
    async def predicate(ctx: Context):
        roles = discord.utils.get(ctx.message.author.roles, id=CONFIG['UWCS_EXEC_ROLE_ID'])
        if roles is None:
            await ctx.message.delete()
            raise BlacklistError(f'You don\'t have permission to run that command, <@{ctx.message.author.id}>.')
        else:
            return True

    return check(predicate)


class Blacklist:
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def blacklist(self, ctx: Context):
        if not ctx.invoked_subcommand:
            await ctx.send("Subcommand not found")

    @blacklist.command(help="Add a topic to the karma blacklist.")
    @is_compsoc_exec()
    async def add(self, ctx: Context, item: str):
        author_id = db_session.query(User).filter(User.user_uid == ctx.message.author.id).first().id

        if not db_session.query(BlockedKarma) \
                .filter(BlockedKarma.name == item.casefold()).all():
            blacklist = BlockedKarma(name=item.casefold(), added_by=author_id)
            db_session.add(blacklist)
            db_session.commit()
            await ctx.send(f'Added {item} to the karma blacklist. :pencil:')
        else:
            await ctx.send(
                f'{item} is already in the karma blacklist. :page_with_curl:')

    @blacklist.command(help="Remove a word from the karma blacklist.")
    @is_compsoc_exec()
    async def remove(self, ctx: Context, item: str):
        if not db_session.query(BlockedKarma).filter(BlockedKarma.name == item.casefold()).all():
            await ctx.send(f'{item} is not in the karma blacklist. :page_with_curl:')
        else:
            db_session.query(BlockedKarma).filter(BlockedKarma.name == item.casefold()).delete()
            db_session.commit()

            await ctx.send(f'{item} has been removed from the karma blacklist. :pencil:')

    @blacklist.command(help="List all blacklisted karma topics.")
    @is_compsoc_exec()
    async def list(self, ctx: Context):
        items = db_session.query(BlockedKarma).all()
        if items:
            list_str = 'The topics in the karma blacklist are:\n\n'

            for item in items:
                list_str += f' • **{item.name}**\n'
        else:
            list_str = 'There are no karma topics currently blacklisted! :mag:'

        await ctx.send(list_str)

    @blacklist.command(help="Search for a blacklisted topic.")
    async def search(self, ctx: Context, item: str):
        item_folded = item.replace('*', '%').casefold()
        items = db_session.query(BlockedKarma) \
            .filter(BlockedKarma.name.ilike(f'%{item_folded}%')).all()
        if len(items) == 0:
            await ctx.send(
                f'There were no topics matching "{item}" in the blacklist. :sweat:')
        else:
            if len(items) == 1:
                list_str = f'The topic matching "{item}" in the blacklist is:\n\n'
            else:
                list_str = f'The {"first 10" if len(items) > 10 else ""} topic matching "{item}" in the blacklist are:\n\n'

            # Don't want to spam too much on a search
            max_len = 10
            for it in items:
                if max_len > 0:
                    list_str += f' • **{it.name}**\n'
                else:
                    break
                max_len -= 1

            await ctx.send(list_str)

    @list.error
    @add.error
    @remove.error
    async def blacklist_error_handler(self, ctx: Context, error: BlacklistError):
        await ctx.send(error.message)


def setup(bot: Bot):
    bot.add_cog(Blacklist(bot))
