from discord.ext import commands
from discord.ext.commands import Context, Bot

LONG_HELP_TEXT = """

"""
SHORT_HELP_TEXT = """
View information about karma topics
"""


class Karma:
    def __init__(self, bot):
        self.bot = bot

    @commands.group(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def karma(self, ctx: Context):
        if not ctx.invoked_subcommand:
            await ctx.send("Subcommand not found")

    @karma.command()
    async def top(self, ctx: Context):
        pass

    @karma.command()
    async def bottom(self, ctx: Context):
        pass

    @karma.command()
    async def info(self, ctx: Context):
        pass

    @karma.command()
    async def plot(self, ctx: Context):
        pass


def setup(bot: Bot):
    bot.add_cog(Karma(bot))
