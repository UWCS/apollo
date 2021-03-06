from datetime import datetime
from decimal import Decimal

from discord import User
from discord.ext.commands import Bot, Cog, Context, check, command, group
from sqlalchemy.exc import SQLAlchemyError

from utils import is_decimal
from models import CountingRun, CountingUser, db_session, User as UserModel

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
        # If user does not use a subcommand assume they want to play the game
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
            started_at = datetime.utcnow()
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
            # Dict for users to correct replies
            # NB no points for the first user - the initial message cannot be wrong
            players = dict()

            while True:
                # Wait for the next numeric message
                msg = await self.bot.wait_for("message", check=check_dec)
                value = Decimal(msg.content)
                if msg.author.id not in players:
                    players[msg.author.id] = 0
                if value == count + step:
                    # If the number is correct, increase the count and length.
                    count += step
                    length += 1
                    players[msg.author.id] += 1
                    await msg.add_reaction("✅")
                else:
                    # Otherwise, break the chain.
                    await msg.add_reaction("❌")
                    await ctx.send(
                        f"Gone wrong at {count}! The next number was {count + step}.\n"
                        f"This chain lasted {length} consecutive messages."
                    )
                    break

            # Save this run to the database
            ended_at = datetime.utcnow()
            run = CountingRun(
                started_at=started_at,
                ended_at=ended_at,
                length=length,
                step=step,
            )
            db_session.add(run)

            # Save the players who played into the database
            for player, correct in players.items():
                # The last message sent is the incorrect one
                wrong = 1 if msg.author.id == player else 0
                db_user = db_session.query(UserModel).filter(UserModel.user_uid == player).first()
                # If we can't find the user, skip
                if not db_user:
                    continue
                # See if they've taken part in the counting game before
                counting_user = db_session.query(CountingUser).filter(
                    CountingUser.user_id == db_user.id).one_or_none()
                if counting_user is None:
                    # Create a new entry
                    counting_user = CountingUser(user_id=db_user.id, correct_replies=correct, wrong_replies=wrong)
                else:
                    counting_user.correct_replies += correct
                    counting_user.wrong_replies += wrong
                db_session.add(counting_user)

            try:
                db_session.commit()
                await ctx.send("Run recorded!")
            except SQLAlchemyError:
                db_session.rollback()
                await ctx.send("Something went wrong. The run could not be recorded.")

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
