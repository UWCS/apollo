
from discord import AllowedMentions
from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content

from utils import get_name_string
from utils.splitutils import split_args

LONG_HELP_TEXT = """
Allows running of various types of votes: FPTP, STV, etc. (WIP)
"""

SHORT_HELP_TEXT = """Allows running of various types of votes"""


class Vote(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def vote(self, ctx: Context):
        if not ctx.invoked_subcommand:
            await ctx.send("Subcommand not found")

    @vote.command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def quick(self, ctx: Context, title: str, *args: clean_content):
        display_name = get_name_string(ctx.message)
        choices = split_args(" ".join(args))
        await ctx.send(f"**Quick Vote: {title}** for {display_name}" +
                       "".join(f"\n\ta{i}: {c}" for i, c in enumerate(choices)),
                       allowed_mentions=AllowedMentions.none())



def setup(bot: Bot):
    bot.add_cog(Vote(bot))
