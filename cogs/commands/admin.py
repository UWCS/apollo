from datetime import datetime
from enum import Enum, unique

import discord
from discord import Color, Embed, TextChannel
from discord.abc import PrivateChannel
from discord.ext import commands
from discord.ext.commands import Bot, CommandError, Context, check
from pytz import timezone, utc
from sqlalchemy.exc import SQLAlchemyError

from cogs.commands.karma import current_milli_time
from config import CONFIG
from models import IgnoredChannel, LoggedMessage, MiniKarmaChannel, User, db_session
from utils import get_name_string, pluralise

LONG_HELP_TEXT = """
A set of administrative utility commands to make life easier.
"""
SHORT_HELP_TEXT = "Admin-only commands."


class AdminError(CommandError):
    message = None

    def __init__(self, message=None, *args):
        self.message = message
        super().__init__(*args)


class EnumGet:
    """Only use this if you're an enum inheriting it!"""

    @classmethod
    def get(cls, argument: str, default=None):
        values = {e.name.casefold(): e.name for e in list(cls)}
        casefolded = argument.casefold()
        if casefolded not in values:
            return default
        else:
            return cls[values[casefolded]]


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


async def is_compsoc_exec_in_guild(ctx: Context):
    # Get the roles of the user in the UWCS discord
    compsoc_guild = [
        guild for guild in ctx.bot.guilds if guild.id == CONFIG.UWCS_DISCORD_ID
    ][0]
    compsoc_member = compsoc_guild.get_member(ctx.message.author.id)
    if not compsoc_member:
        raise AdminError(
            f"You aren't part of the UWCS discord so I'm afraid I can't let you do that. :octagonal_sign:"
        )

    roles = list(
        map(
            lambda x: discord.utils.get(compsoc_member.roles, id=x),
            CONFIG.UWCS_EXEC_ROLE_IDS,
        )
    )
    if not roles:
        if not isinstance(ctx.channel, PrivateChannel):
            await ctx.message.delete()
        display_name = get_name_string(ctx.message)
        raise AdminError(
            f"You don't have permission to run that command, {display_name}."
        )
    else:
        return True


class Admin(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
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
        self, ctx: Context, channel: TextChannel, mode: ChannelIgnoreMode.get = None
    ):
        ignored_channel = (
            db_session.query(IgnoredChannel)
            .filter(IgnoredChannel.channel == channel.id)
            .first()
        )

        if mode == ChannelIgnoreMode.Ignore:
            if ignored_channel is None:
                # Create a new entry
                user = (
                    db_session.query(User)
                    .filter(User.user_uid == ctx.author.id)
                    .first()
                )
                new_ignored_channel = IgnoredChannel(
                    channel=channel.id,
                    user_id=user.id,
                )
                db_session.add(new_ignored_channel)
                try:
                    db_session.commit()
                    await ctx.send(f"Added {channel.mention} to the ignored list.")
                except SQLAlchemyError:
                    db_session.rollback()
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
                except SQLAlchemyError:
                    db_session.rollback()
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
        self, ctx: Context, channel: TextChannel, mode: MiniKarmaMode.get = None
    ):
        # TODO: avoid writing duplicate code with above if possible?
        karma_channel = (
            db_session.query(MiniKarmaChannel)
            .filter(MiniKarmaChannel.channel == channel.id)
            .first()
        )

        if mode == MiniKarmaMode.Mini:
            if karma_channel is None:
                user = (
                    db_session.query(User)
                    .filter(User.user_uid == ctx.author.id)
                    .first()
                )
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
                except SQLAlchemyError:
                    db_session.rollback()
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
                except SQLAlchemyError:
                    db_session.rollback()
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
        ignored_channels = [
            f" • {c.mention}"
            for c in ctx.guild.text_channels
            if c.id in list(db_session.query(IgnoredChannel).all())
        ]

        mini_karma_channels = [
            f" • {c.mention}"
            for c in ctx.guild.text_channels
            if c.id in (list(db_session.query(MiniKarmaChannel).all()))
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

    @admin.command(
        name="userinfo",
        help="Display information about the given user. Uses their Discord username.",
        brief="Show info about a user using their Discord username.",
    )
    @check(is_compsoc_exec_in_guild)
    async def user_info(self, ctx: Context, user_str: str):
        await ctx.trigger_typing()

        t_start = current_milli_time()
        # Find the user in the database
        users = [
            user
            for user in db_session.query(User).all()
            if user_str.casefold() in user.username.casefold()
        ]
        if not users:
            raise AdminError(f'Cannot find any user(s) matching "{user_str}".')

        if len(users) > 1:
            raise AdminError(
                f'Found more than one with the search term "{user_str}", can you be more specific?'
            )

        user = users[0]

        # Create the embed to send
        embed_colour = Color.from_rgb(61, 83, 255)
        embed_title = f"User info for {user.username}"
        embed = Embed(title=embed_title, color=embed_colour)
        embed.add_field(
            name="First seen",
            value=f'{user.username.split("#")[0]} was first seen on {datetime.strftime(user.first_seen, "%d %b %Y at %H:%M")}.',
        )
        embed.add_field(
            name="Last seen",
            value=f'{user.username.split("#")[0]} was last seen on {datetime.strftime(user.last_seen, "%d %b %Y at %H:%M")}.',
        )
        if user.verified_at:
            embed.add_field(
                name="Verification",
                value=f'{user.username.split("#")[0]} is a verified member of CompSoc with a Uni ID of {user.uni_id} having verified on {datetime.strftime(user.verified_at, "%d %b %Y at %H:%M")}.',
            )

        posts = (
            db_session.query(LoggedMessage)
            .filter(LoggedMessage.author == user.id)
            .all()
        )
        channels = (
            db_session.query(LoggedMessage.channel_name)
            .filter(LoggedMessage.author == user.id)
            .group_by(LoggedMessage.channel_name)
            .all()
        )
        embed.add_field(
            name="Message count",
            value=f'{user.username.split("#")[0]} has posted {len(posts)} {pluralise(posts, "time")} across {len(channels)} {pluralise(channels, "channel")}.',
        )

        # Generate stats information
        time_taken = (current_milli_time() - t_start) / 1000
        generated_at = datetime.strftime(
            utc.localize(datetime.utcnow()).astimezone(timezone("Europe/London")),
            "%H:%M %d %b %Y",
        )
        embed.set_footer(
            text=f"Information generated at {generated_at} in {time_taken:.3f} seconds"
        )

        await ctx.send(embed=embed)

    @admin.error
    async def user_info_error(self, ctx: Context, error: AdminError):
        await ctx.send(error.message)


def setup(bot: Bot):
    bot.add_cog(Admin(bot))
