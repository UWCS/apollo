import logging
from enum import Enum, unique

from discord import TextChannel
from discord.ext import commands
from discord.ext.commands import Bot, Context, check
from sqlalchemy.exc import SQLAlchemyError

from cogs.commands.karma import current_milli_time
from models import db_session
from models.karma import IgnoredChannel, MiniKarmaChannel
from utils import EnumGet, get_database_user, is_compsoc_exec_in_guild

LONG_HELP_TEXT = """
A set of administrative utility commands to make life easier.
"""
SHORT_HELP_TEXT = "Admin-only commands."


@unique
class ChannelIgnoreMode(EnumGet, Enum):
    """Whether a channel is ignored or not"""

    Ignore = 0
    Watch = 1


@unique
class MiniKarmaMode(EnumGet, Enum):
    """Whether a channel is on mini-karma mode or not"""

    Mini = 0
    Normal = 1


class Admin(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_group(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    @check(is_compsoc_exec_in_guild)
    async def admin(self, ctx: Context):
        if not ctx.invoked_subcommand:
            await ctx.send("Subcommand not found")

    @admin.command(
        name="channel",
        help="""Gets or sets whether the specified channel is being ignored or not.
        Ignored channels do not react to commands but still track karma.

        Expects up to two arguments: !admin channel (channel) [ignore|watch].
        If one argument is passed, retrieve the current setting.
        If two arguments are passed, set whether the channel is ignored or not.
        """,
        brief="Ignore or respond to commands in the given channel",
    )
    async def channel_ignore(
        self, ctx: Context, channel: TextChannel, mode: ChannelIgnoreMode = None
    ):
        ignored_channel = (
            db_session.query(IgnoredChannel)
            .filter(IgnoredChannel.channel == channel.id)
            .first()
        )

        if mode == ChannelIgnoreMode.Ignore:
            if ignored_channel is None:
                # Create a new entry
                user = get_database_user(ctx.author)
                new_ignored_channel = IgnoredChannel(
                    channel=channel.id,
                    user_id=user.id,
                )
                db_session.add(new_ignored_channel)
                try:
                    db_session.commit()
                    await ctx.send(f"Added {channel.mention} to the ignored list.")
                except SQLAlchemyError as e:
                    db_session.rollback()
                    logging.exception(e)
                    await ctx.send("Something went wrong. No change has occurred.")
            else:
                # Entry already present
                await ctx.send(f"{channel.mention} is already ignored!")
        elif mode == ChannelIgnoreMode.Watch:
            if ignored_channel is not None:
                # Remove the entry
                db_session.query(IgnoredChannel).filter(
                    IgnoredChannel.channel == channel.id
                ).delete()
                try:
                    db_session.commit()
                    await ctx.send(f"{channel.mention} is no longer being ignored.")
                except SQLAlchemyError as e:
                    db_session.rollback()
                    logging.exception(e)
                    await ctx.send("Something went wrong. No change has occurred.")
            else:
                # The entry is not present
                await ctx.send(f"{channel.mention} is not currently being ignored.")

        else:
            # Report status
            if ignored_channel is not None:
                await ctx.send(f"{channel.mention} is currently being ignored.")
            else:
                await ctx.send(f"{channel.mention} is not currently being ignored")

    @admin.command(
        name="minikarma",
        help="""Gets or sets whether the specified channel is using mini-karma output mode or not.
        Mini-karma output channels have a more brief karma message, designed to reduce number of newlines.
        
        Expects up to two arguments: !admin minikarma (channel) [mini|normal]
        If one argument is passed, retrieve the current settings.
        If two arguments are passed, set whether the channel is using mini-karma or not.
        """,
        brief="Send a shorter karma message in the given channel",
    )
    async def channel_karma(
        self, ctx: Context, channel: TextChannel, mode: MiniKarmaMode = None
    ):
        # TODO: avoid writing duplicate code with above if possible?
        karma_channel = (
            db_session.query(MiniKarmaChannel)
            .filter(MiniKarmaChannel.channel == channel.id)
            .first()
        )

        if mode == MiniKarmaMode.Mini:
            if karma_channel is None:
                user = get_database_user(ctx.author)
                new_karma_channel = MiniKarmaChannel(
                    channel=channel.id,
                    user_id=user.id,
                )
                db_session.add(new_karma_channel)
                try:
                    db_session.commit()
                    await ctx.send(
                        f"Added {channel.mention} to the mini-karma channels"
                    )
                except SQLAlchemyError as e:
                    db_session.rollback()
                    logging.exception(e)
                    await ctx.send("Something went wrong. No change has occurred.")
            else:
                await ctx.send(f"{channel.mention} is already on mini-karma mode!")
        elif mode == MiniKarmaMode.Normal:
            if karma_channel is not None:
                db_session.query(MiniKarmaChannel).filter(
                    MiniKarmaChannel.channel == channel.id
                ).delete()
                try:
                    db_session.commit()
                    await ctx.send(f"{channel.mention} is now on normal karma mode")
                except SQLAlchemyError as e:
                    db_session.rollback()
                    logging.exception(e)
                    await ctx.send("Something went wrong. No change has occurred")
            else:
                await ctx.send(f"{channel.mention} is already on normal karma mode!")
        else:
            if karma_channel is None:
                await ctx.send(f"{channel.mention} is on normal karma mode.")
            else:
                await ctx.send(f"{channel.mention} is on mini-karma mode.")

    @admin.command(
        name="list",
        help="""List the channels that are ignored or on mini-karma mode""",
    )
    async def channel_ignore_list(self, ctx: Context):
        ignored = set(c.channel for c in db_session.query(IgnoredChannel).all())
        ignored_channels = [
            f" • {c.mention}" for c in ctx.guild.text_channels if c.id in ignored
        ]

        mini = set(c.channel for c in db_session.query(MiniKarmaChannel).all())
        mini_karma_channels = [
            f" • {c.mention}" for c in ctx.guild.text_channels if c.id in mini
        ]

        message = []

        if ignored_channels:
            message += ["Ignored channels:"] + ignored_channels

        if ignored_channels and mini_karma_channels:
            message.append("")

        if mini_karma_channels:
            message += ["", "Mini-karma Channels:"] + mini_karma_channels

        if message:
            await ctx.send("\n".join(message))
        else:
            await ctx.send("No channels are ignored or on mini-karma mode.")


async def setup(bot: Bot):
    await bot.add_cog(Admin(bot))
