from discord.ext import commands
from discord.ext.commands import Context, Bot, clean_content

LONG_HELP_TEXT = """
Very important command.
"""

SHORT_HELP_TEXT = """Very important command."""


class Zed0:
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def zed0(self, ctx: Context):
        await ctx.send("¬_¬")

def setup(bot: Bot):
    bot.add_cog(Zed0(bot))
