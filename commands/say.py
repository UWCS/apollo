from discord.ext import commands
from discord.ext.commands import Context, Bot, clean_content

LONG_HELP_TEXT = """
Make the bot repeat after you.
"""

SHORT_HELP_TEXT = """Make the bot repeat after you."""


class Say(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def say(self, ctx: Context, *message: clean_content):
        await ctx.send(" ".join([x.lstrip("@") for x in message]))


def setup(bot: Bot):
    bot.add_cog(Say(bot))
