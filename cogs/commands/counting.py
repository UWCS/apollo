from discord import Message
from discord.ext import commands
from discord.ext.commands import Bot, Cog, Context, clean_content

from utils import get_name_string

LONG_HELP_TEXT = """
Starts a counting game where each player must name the next number in the sequence until someone names an invalid number
"""

SHORT_HELP_TEXT = """Starts a counting game"""


class Counting(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.reset()

    def reset(self):
        self.currentlyPlaying = False
        self.channel = None
        self.nextNumber = 0

    @commands.command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def counting(self, ctx: Context):
        if self.currentlyPlaying:
            channel = (
                "this channel"
                if self.channel == ctx.message.channel
                else self.channel.mention
            )
            await ctx.send(f"There is already a game being played in {channel}!")
            return

        self.currentlyPlaying = True
        self.channel = ctx.message.channel

        await ctx.send(f"The game begins!")

    @Cog.listener()
    async def on_message(self, message: Message):
        if not self.currentlyPlaying or message.channel != self.channel:
            return
        if message.content.isnumeric():
            if int(message.content) == self.nextNumber:
                self.nextNumber += 1
                await message.add_reaction("✅")
            else:
                await message.add_reaction("❌")
                await message.channel.send(
                    f"**Incorrect number!** The next number was {self.nextNumber}."
                )
                self.reset()


def setup(bot: Bot):
    bot.add_cog(Counting(bot))
