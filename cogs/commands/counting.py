from decimal import Decimal

from discord import Message
from discord.ext import commands
from discord.ext.commands import Bot, Cog, Context, clean_content

from utils import get_name_string, is_number

LONG_HELP_TEXT = """
Starts a counting game where each player must name the next number in the sequence until someone names an invalid number
"""

SHORT_HELP_TEXT = """Starts a counting game"""


class Counting(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.reset()

    def reset(self):
        self.currently_playing = False
        self.channel = None
        self.prev_number = None
        self.step = None

    @commands.command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def counting(self, ctx: Context):
        if self.currently_playing:
            channel = (
                "this channel"
                if self.channel == ctx.message.channel
                else self.channel.mention
            )
            await ctx.send(f"There is already a game being played in {channel}!")
            return

        self.currently_playing = True
        self.channel = ctx.message.channel

        await ctx.send(f"The game begins!")

    @Cog.listener()
    async def on_message(self, message: Message):
        if not self.currently_playing or message.channel != self.channel:
            return
        if is_number(message.content):
            number = Decimal(message.content)
            if self.prev_number == None:  # First number submitted
                self.prev_number = number
                if number != 0:
                    self.step = number
            elif self.step == None:  # First non-zero number submitted
                self.prev_number = number
                self.step = number
            elif number == self.prev_number + self.step:  # General case
                self.prev_number = number
                await message.add_reaction("✅")
            else:  # Invalid submission
                await message.add_reaction("❌")
                await message.channel.send(
                    f"**Incorrect number!** The next number was {self.next_number}."
                )
                self.reset()


def setup(bot: Bot):
    bot.add_cog(Counting(bot))
