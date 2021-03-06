from decimal import Decimal

from discord import User
from discord.ext.commands import Bot, Cog, Context, check, command, group

from utils import is_decimal

LONG_HELP_TEXT = """
Starts a counting game where each player must name the next number in the sequence until someone names an invalid number
"""

SHORT_HELP_TEXT = """Starts a counting game"""


class Counting(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.currently_playing = False
        self.channel = None

    @group(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def counting(self, ctx: Context):
        if not ctx.invoked_subcommand:
            if self.currently_playing:
                channel = (
                    "this channel"
                    if self.channel == ctx.message.channel
                    else self.channel.mention
                )
                await ctx.send(f"There is already a game being played in {channel}!")
                return

            self.currently_playing = True
            channel = ctx.message.channel

            await ctx.send(f"The game begins!")
            # The count starts at 0.
            count = 0
            # The number of successful replies in a row.
            length = 0
            # We need to determine what the step is.
            # It will be the first decimal number sent in the same channel.

            def check_dec(m):
                return m.channel == channel and is_decimal(m.content)

            msg = await self.bot.wait_for("message", check=check)
            # Set the step.
            await msg.add_reaction("✅")
            step = Decimal(msg.content)
            length += 1
            count += step

            while True:
                # Wait for the next numeric message
                msg = await self.bot.wait_for("message", check=check_dec)
                value = Decimal(msg.content)
                if value == count + step:
                    # If the number is correct, increase the count and length.
                    count += step
                    length += 1
                    await msg.add_reaction("✅")
                else:
                    # Otherwise, break the chain.
                    await msg.add_reaction("❌")
                    await ctx.send(
                        f"Gone wrong at {count}! The next number was {count + step}.\n"
                        f"This chain lasted {length} consecutive messages."
                    )
                    break

            # Reset the cog's state.
            self.currently_playing = False
            self.channel = None

    @counting.command(help="Show the top 5 users in the counting game")
    async def leaderboard(self, ctx: Context):
        pass

    @counting.command(help="Show the top 5 longest runs recorded")
    async def runs(self, ctx: Context):
        pass

    @counting.command(help="Look up a user's stats")
    async def lookup(self, ctx: Context, user: User):
        pass

    @counting.command(help="Look up your own stats")
    async def me(self, ctx: Context):
        await self.lookup(ctx, ctx.author)


def setup(bot: Bot):
    bot.add_cog(Counting(bot))
