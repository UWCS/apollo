from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content

from utils import get_name_string

LONG_HELP_TEXT = """
Starts a counting game where each player must name the next number in the sequence until someone names an invalid number
"""

SHORT_HELP_TEXT = """Starts a counting game"""


class Counting(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        reset()

    def reset(self):
        self.currentlyPlaying = False
        self.channel = None
        self.nextNumber = 0

    @commands.command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def counting(self, ctx: Context, *args: clean_content):
        if self.currentlyPlaying:
            await ctx.send(f"There is already a game being played in {self.channel}!")
            return

        self.currentlyPlaying = True
        self.channel = ctx.message.channel

        await ctx.send(f"The game begins!")

    @Cog.listener()
    async def on_message(self, message: Message):
        if not currentlyPlaying or message.channel != self.channel:
            return
        if message.content.isnumeric():
            if int(message.content) == nextNumber:
                message.add_reaction("✔️")
            else:
                message.add_reaction("❌")
                await ctx.send(f"**Incorrect number!** The next number was {self.nextNumber}.")
                reset ()


def setup(bot: Bot):
    bot.add_cog(Flip(bot))
