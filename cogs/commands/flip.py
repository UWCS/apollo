import random
import shlex

from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content

from utils import get_name_string

LONG_HELP_TEXT = """
Picks randomly between two options (or heads and tails if left blank)
"""

SHORT_HELP_TEXT = """Picks randomly between two options"""


class Flip(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def flip(self, ctx: Context, *, args: str = ""):
        args = await clean_content().convert(ctx, args)
        args = shlex.split(args)
        display_name = get_name_string(ctx.message)

        if len(args) == 1:
            await ctx.send(f"I can't flip just one item {display_name}! :confused:")
        else:
            options = ["Heads", "Tails"] if not args else args

            await ctx.send(f'{display_name}: {random.choice(options).lstrip("@")}')


async def setup(bot: Bot):
    await bot.add_cog(Flip(bot))
