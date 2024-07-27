import random
import shlex
import string
from typing import List

from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content

from utils import get_name_string

LONG_HELP_TEXT = """
Shakes a Magic 8-ball to determine the answer to any question you ask e.g. `!8ball should I get a takeaway?`
"""

SHORT_HELP_TEXT = """Asks a question to a Magic 8-ball"""


class EightBall(commands.Cog):
    def __init__(self, bot: Bot, options: List[string]):
        self.bot = bot
        self.options = options

    @commands.hybrid_command(name="8ball", help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def execute(self, ctx: Context, *, args: str = ""):
        args = await clean_content().convert(ctx, args)
        args = shlex.split(args)
        display_name = get_name_string(ctx.message)

        if len(args) == 1:
            await ctx.send(f"You must pose the Magic 8-ball a dilemma {display_name}!")
        else:
            await ctx.send(f"{display_name}: {(random.choice(self.options))}")


async def setup(bot: Bot):
    options = [
        # Positive
        "It is certain",
        "It is decidedly so",
        "Without a doubt",
        "Yes definitely",
        "You may rely on it",
        "As I see it, yes",
        "Most likely",
        "Outlook good",
        "Yes",
        "Signs point to yes",
        # Indeterminate
        "Reply hazy, try again",
        "Ask again later",
        "Better not tell you now",
        "Cannot predict now",
        "Concentrate and ask again",
        # Negative
        "Don't count on it",
        "My reply is no",
        "My sources say no",
        "Outlook not so good",
        "Very doubtful",
    ]

    await bot.add_cog(EightBall(bot, options))
