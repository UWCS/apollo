import re
from datetime import datetime

import discord
from discord import Embed, Color
from discord.abc import PrivateChannel
from discord.ext import commands
from discord.ext.commands import Context, Bot, CommandError, check, clean_content
from pytz import utc, timezone

from apollo import pluralise
from commands.karma import current_milli_time
from commands.verify import is_private_channel
from config import CONFIG
from models import db_session, User, LoggedMessage
from utils.aliases import get_name_string

LONG_HELP_TEXT = """
A set of administrative utility commands to make life easier.
"""
SHORT_HELP_TEXT = "Admin-only commands."


class AdminError(CommandError):
    message = None

    def __init__(self, message=None, *args):
        self.message = message
        super().__init__(*args)


def is_compsoc_exec_in_guild():
    """
    Check if the user that ran the command is authorised to do so
    """

    async def predicate(ctx: Context):
        # Get the roles of the user in the UWCS discord
        compsoc_guild = [
            guild for guild in ctx.bot.guilds if guild.id == CONFIG["UWCS_DISCORD_ID"]
        ][0]
        compsoc_member = compsoc_guild.get_member(ctx.message.author.id)
        if not compsoc_member:
            raise AdminError(
                f"You aren't part of the UWCS discord so I'm afraid I can't let you do that. :octagonal_sign:"
            )

        roles = list(
            map(
                lambda x: discord.utils.get(compsoc_member.roles, id=x),
                CONFIG["UWCS_EXEC_ROLE_IDS"],
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

    return check(predicate)


class Admin(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def admin(self, ctx: Context):
        if not ctx.invoked_subcommand:
            await ctx.send("Subcommand not found")

    # @admin.command(
    #     name="channel",
    #     help="""Ignore or respond to commands in the given channel (while keeping eyes on Karma).
    #
    #     Expects 2 arguments, whether or not to ignore a channel (ignore, watch) and the channel (ID or link)""",
    #     bried="Ignore or respond to commands in the given channel",
    # )
    async def channel_ignore(self, ctx: Context, *args: clean_content):
        # Format: !admin channel (ignore|watch) <channels...> (channel is ID or channel link)
        # Make sure there's the right number of args
        if len(args) < 2:
            await ctx.send(
                "I need both the channel(s) to ignore and whether I should watch or ignore them. See the help command for more info :smile:"
            )
            return

        # Make sure the mode is correct
        mode = str(args[0]).lower()
        if mode != "ignore" and mode != "watch":
            await ctx.send(
                f'I can only "watch" or "ignore" channels, you told me to {mode} :slight_frown:'
            )
            return

        # Get each of the channels from the guild
        channel_link_exp = re.compile(r"^<#(?P<id>\d+)>$")
        channel_id_exp = re.compile(r"^\d+$")
        channels_raw = list(args)[1:]
        compsoc_guild = [
            guild for guild in ctx.bot.guilds if guild.id == CONFIG["UWCS_DISCORD_ID"]
        ][0]

        error_not_id = []
        channel_ids = []
        for c in channels_raw:
            if channel_id_exp.match(c):
                channel_ids.append(int(c))
            else:
                link_match = channel_link_exp.match(c)
                if link_match:
                    groups = link_match.groupdict()
                    channel_ids.append(int(groups.get("id")))
                else:
                    error_not_id.append(c)

        # Check each channel is in the guild
        channels = []
        error_nin_guild = []
        for chan_id in channel_ids:
            channel = discord.utils.get(compsoc_guild.channels, id=chan_id)
            if channel:
                channels.append(channel)
            else:
                error_nin_guild.append(chan_id)

        # TODO: Check they're in the guild, and then do the DB action
        await ctx.send(" ".join(args))

    @admin.command(
        name="userinfo",
        help="Display information about the given user. Uses their Discord username.",
        brief="Show info about a user using their Discord username.",
    )
    @is_compsoc_exec_in_guild()
    @is_private_channel()
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

        # Generate stats information
        time_taken = (current_milli_time() - t_start) / 1000
        generated_at = datetime.strftime(
            utc.localize(datetime.utcnow()).astimezone(timezone("Europe/London")),
            "%H:%M %d %b %Y",
        )

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
        embed.set_footer(
            text=f"Information generated at {generated_at} in {time_taken:.3f} seconds"
        )

        await ctx.send(embed=embed)

    @user_info.error
    async def user_info_error(self, ctx: Context, error: AdminError):
        await ctx.send(error.message)


def setup(bot: Bot):
    bot.add_cog(Admin(bot))
