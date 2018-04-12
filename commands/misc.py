from discord.ext import commands
from discord.ext.commands import Context, Bot
from models import db_session, Blacklist, User

ZED0_HELP_TEXT = """Very important command."""
FAUX_HELP_TEXT = """A member of the rust evangelical strike force."""


class Misc:
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(help=ZED0_HELP_TEXT, brief=ZED0_HELP_TEXT)
    async def zed0(self, ctx: Context):
        await ctx.send("¬_¬")

    @commands.command(help=FAUX_HELP_TEXT, brief=FAUX_HELP_TEXT)
    async def faux(self, ctx: Context):
        await ctx.send("RUST")

    @commands.command(help="List all blacklisted karma items.")
    async def blacklist_list(self, ctx: Context):
        blk_lst = f'Items in the blacklist: '
        items = db_session.query(Blacklist).all()
        for item in items:
            blk_lst += f'{item.name}, '
        await ctx.send(blk_lst[:-2])


def setup(bot: Bot):
    bot.add_cog(Misc(bot))
