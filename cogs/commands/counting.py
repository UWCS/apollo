import logging
from datetime import datetime
from decimal import Decimal

from discord import User
from discord.ext.commands import Bot, BucketType, Cog, Context, cooldown, group
from sqlalchemy.exc import SQLAlchemyError

from models import CountingRun, CountingUser
from models import User as UserModel
from models import db_session
from utils import get_database_user_from_id, is_decimal

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
            self.channel = ctx.channel
            started_at = datetime.utcnow()

            await ctx.send(f"The game begins!")
            # The count starts at 0.
            count = 0
            # The number of successful replies in a row.
            length = 0

            # We need to determine what the step is.
            # It will be the first decimal number sent in the same channel.

            def check_dec(m):
                return m.channel == self.channel and is_decimal(m.content)

            msg = await self.bot.wait_for("message", check=check_dec)
            # Set the step.
            await msg.add_reaction("✅")
            step = Decimal(msg.content)
            length += 1
            count += step
            # Dict for users to correct replies
            # NB no points for the first user - the initial message cannot be wrong
            players = dict()
            # Used to make sure someone else replies
            last_player = msg.author

            while True:
                # Wait for the next numeric message sent by a different person in the same channel
                def check_dec_player(m):
                    return check_dec(m) and m.author != last_player

                msg = await self.bot.wait_for("message", check=check_dec_player)
                last_player = msg.author
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
                db_user = get_database_user_from_id(player)
                # If we can't find the user, skip
                if not db_user:
                    continue
                # See if they've taken part in the counting game before
                counting_user = (
                    db_session.query(CountingUser)
                    .filter(CountingUser.user_id == db_user.id)
                    .one_or_none()
                )
                if counting_user is None:
                    # Create a new entry
                    counting_user = CountingUser(
                        user_id=db_user.id, correct_replies=correct, wrong_replies=wrong
                    )
                else:
                    counting_user.correct_replies += correct
                    counting_user.wrong_replies += wrong
                db_session.add(counting_user)

            try:
                db_session.commit()
                await ctx.send("Run recorded!")
            except SQLAlchemyError as e:
                db_session.rollback()
                logging.exception(e)
                await ctx.send("Something went wrong. The run could not be recorded.")

            # Reset the cog's state.
            self.currently_playing = False
            self.channel = None

    @counting.command(help="Show the top 5 users in the counting game")
    async def leaderboard(self, ctx: Context):
        top5 = (
            db_session.query(CountingUser)
            .order_by(CountingUser.correct_replies.desc())
            .limit(5)
            .all()
        )
        message = ["Here are the top 5 users by correct answers: ", ""]
        for i, c_user in enumerate(top5):
            username = (
                db_session.query(UserModel)
                .filter(UserModel.id == c_user.id)
                .first()
                .username
            )
            message.append(
                f"• #{i + 1}. **{username}**: {c_user.correct_replies}✅ {c_user.wrong_replies}❌"
            )

        await ctx.send("\n".join(message))

    @counting.command(help="Show the top 5 longest runs recorded")
    async def top(self, ctx: Context):
        top5 = (
            db_session.query(CountingRun)
            .order_by(CountingRun.length.desc())
            .limit(5)
            .all()
        )
        message = ["Here are the top 5 longest runs:" ""]
        for i, c_run in enumerate(top5):
            start = c_run.started_at.strftime("%x %X")
            end = c_run.ended_at.strftime("%x %X")
            message.append(
                f"• #{i + 1}. **length {c_run.length}**, step {c_run.step}, took place {start}-{end}"
            )

        await ctx.send("\n".join(message))

    @cooldown(2, 30, BucketType.user)
    @counting.command(help="Look up a user's stats")
    async def user(self, ctx: Context, user: User):
        # Give me Result.Bind please
        db_user = (
            db_session.query(UserModel).filter(UserModel.user_uid == user.id).first()
        )
        if db_user is None:
            await ctx.send("Could not find user!")
            return
        c_user = (
            db_session.query(CountingUser).filter(CountingUser.id == db_user.id).first()
        )
        if c_user is None:
            await ctx.send("User has not played any counting games!")
            return
        await ctx.send(
            f"**{db_user.username}**: {c_user.correct_replies}✅ {c_user.wrong_replies}❌"
        )

    @counting.command(help="Look up your own stats")
    async def me(self, ctx: Context):
        await self.user(ctx, ctx.author)

    @user.error
    async def user_error(self, ctx: Context, err):
        await ctx.send(err)


def setup(bot: Bot):
    bot.add_cog(Counting(bot))
