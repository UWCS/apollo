import random

from discord.ext import commands
from discord.ext.commands import Context, Bot, clean_content

LONG_HELP_TEXT = """
Picks randomly between two options (or heads and tails if left blank)
"""

SHORT_HELP_TEXT = """Picks randomly between two options"""


class Flip:
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def flip(self, ctx: Context, *args: clean_content):
        if len(args) == 1:
            await ctx.send(f'I can\'t flip just one item <@{ctx.message.author.id}>! :confused:')
        else:
            options = ['Heads', 'Tails'] if not args else args

            await ctx.send(f'<@{ctx.message.author.id}>: {random.choice(options).title().lstrip("@")}')


def setup(bot: Bot):
    bot.add_cog(Flip(bot))
