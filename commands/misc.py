from discord.ext import commands
from discord.ext.commands import Context, Bot

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


def setup(bot: Bot):
    bot.add_cog(Misc(bot))
