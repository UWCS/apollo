from discord.ext import commands
from discord.ext.commands import Context, Bot

ZED0_HELP_TEXT = """Very important command."""


class Misc:
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(help=ZED0_HELP_TEXT, brief=ZED0_HELP_TEXT)
    async def zed0(self, ctx: Context):
        await ctx.send("¬_¬")


def setup(bot: Bot):
    bot.add_cog(Misc(bot))
