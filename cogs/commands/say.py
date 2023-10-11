from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content

LONG_HELP_TEXT = """
Make the bot repeat after you.
"""

SHORT_HELP_TEXT = """Make the bot repeat after you."""


class Say(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def say(self, ctx: Context, *, message: clean_content):
        await ctx.send(message)


async def setup(bot: Bot):
    await bot.add_cog(Say(bot))
