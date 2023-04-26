from discord.ext import commands
from discord.ext.commands import Bot, Context

import utils
from config import CONFIG

LONG_HELP_TEXT = """
Hapy birthday!!!!

As is tradtion, wish our dear lord chancellor of the computer a happy birthday
"""

SHORT_HELP_TEXT = "Hapy birthday!!!!"


class Birthday(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def birthday(self, ctx: Context):
        await ctx.reply(f"Hapy birthday!!!! <@{CONFIG.LORD_CHANCELLOR_ID}>")


async def setup(bot: Bot):
    await bot.add_cog(Birthday(bot))
