import asyncio
import logging
from datetime import datetime
from functools import cached_property
from textwrap import dedent
from typing import Optional

import humanize
from discord import Guild, HTTPException, Member, Role, TextChannel, User
from discord.ext.commands import Bot, Cog, Context, Greedy, check, command, group
from discord.utils import get
from sqlalchemy.exc import SQLAlchemyError

import models
from config import CONFIG
from models import ModerationAction, ModerationHistory, db_session
from utils import (
    AdminError,
    DateTimeConverter,
    format_list,
    format_list_of_members,
    get_database_user,
    is_compsoc_exec_in_guild,
)
from utils.Greedy1 import Greedy1Command, Greedy1Group


def add_moderation_history_item(
    user, action, reason, moderator, until=None, linked_item=None
):
    user_id = (
        db_session.query(models.User).filter(models.User.user_uid == user.id).first().id
    )
    moderator_id = (
        db_session.query(models.User)
        .filter(models.User.user_uid == moderator.id)
        .first()
        .id
    )
    complete = (
        False
        if action in (ModerationAction.TEMPMUTE, ModerationAction.TEMPBAN)
        else None
    )
    moderation_history = ModerationHistory(
        user_id=user_id,
        action=action,
        until=until,
        complete=complete,
        reason=reason,
        moderator_id=moderator_id,
        linked_item=linked_item,
    )
    db_session.add(moderation_history)
    try:
        db_session.commit()
    except SQLAlchemyError as e:
        db_session.rollback()
        logging.error(e)


class Moderation(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.loop = bot.loop.create_task(self.temp_action_loop())

    async def cog_unload(self):
        self.loop.cancel()

    @cached_property
    def emoji(self):
        return {
            "no": get(self.bot.emojis, id=840911865830703124),
            "what": get(self.bot.emojis, id=840917271111008266),
            "warn": get(self.bot.emojis, id=840911836580544512),
            "yes": get(self.bot.emojis, id=840911879886209024),
        }

    @cached_property
    def uwcs_guild(self) -> Guild:
        return get(self.bot.guilds, id=CONFIG.UWCS_DISCORD_ID)

    @cached_property
    def mute_role(self) -> Role:
        return get(self.uwcs_guild.roles, id=840929051053129738)

    async def temp_action_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            now = datetime.now()
            to_repeal = (
                db_session.query(ModerationHistory)
                .filter(
                    ModerationHistory.action.in_(
                        (ModerationAction.TEMPMUTE, ModerationAction.TEMPBAN)
                    ),
                    ModerationHistory.complete == False,
                    ModerationHistory.until <= now,
                )
                .all()
            )

            bans = None

            for item in to_repeal:
                db_user = (
                    db_session.query(models.User)
                    .filter(models.User.id == item.user_id)
                    .one_or_none()
                )
                moderator = (
                    db_session.query(models.User.username)
                    .filter(models.User.id == item.moderator_id)
                    .one_or_none()
                )
                date = humanize.naturaldate(item.timestamp)
                if item.action == ModerationAction.TEMPMUTE:
                    user = get(self.uwcs_guild.members, id=db_user.user_uid)
                    reason = f"Removing tempmute on {db_user.username} placed by {moderator} {date}."
                    item.complete = True
                    logging.info(reason)
                    await user.remove_roles(self.mute_role, reason=reason)
                elif item.action == ModerationAction.TEMPBAN:
                    if bans is None:
                        bans = await self.uwcs_guild.bans()
                    user = get(bans, user__id=db_user.user_uid)
                    reason = f"Removing tempban on {db_user.username} placed by {moderator} {date}."
                    item.complete = True
                    await self.uwcs_guild.unban(user, reason=reason)

            try:
                db_session.commit()
            except SQLAlchemyError as e:
                db_session.rollback()
                logging.error(e)

            await asyncio.sleep(CONFIG.REMINDER_SEARCH_INTERVAL)

    def only_mentions_users(self, react=False):
        async def predicate(ctx):
            ret = not (
                ctx.message.mention_everyone or len(ctx.message.role_mentions) > 0
            )
            if not ret and react:
                await ctx.message.add_reaction(self.emoji["no"])
            return ret

        return check(predicate)

    async def cog_check(self, ctx):
        if not await is_compsoc_exec_in_guild(ctx):
            raise AdminError("You don't have permission to run this command.")
        return True

    async def cog_command_error(self, ctx, error):
        logging.error(error)
        await ctx.message.add_reaction(self.emoji["no"])

    @command(cls=Greedy1Command)
    @only_mentions_users(True)
    async def tempmute(
        self,
        ctx: Context,
        members: Greedy[Member],
        until: DateTimeConverter,
        *,
        reason: Optional[str],
    ):
        muted = []
        failed = []

        logging.info(f"{ctx.author} used tempmute until {until} with reason {reason}")
        for member in members:
            try:
                await member.add_roles(self.mute_role, reason=reason)
                add_moderation_history_item(
                    member, ModerationAction.TEMPMUTE, reason, ctx.author, until
                )
                logging.info(f"Tempmuted {member}")
                muted.append(member)
            except HTTPException:
                logging.info(f"Failed to tempmute {member}")
                failed.append(member)

        message_parts = []

        if len(muted) > 0:
            mentions = format_list_of_members(failed)
            were = "were" if len(muted) > 1 else "was"
            until_datetime = f"until {humanize.naturaltime(until)} (a duration of {humanize.precisedelta(until - datetime.now())})"
            with_reason = (
                "with no reason given"
                if reason is None
                else f"with the reason \n> {reason}"
            )
            message_parts.append(
                dedent(
                    """
                    :speaker: **TEMPMUTED** :speaker:
                    {mentions} {were} tempmuted {until_datetime} {with_reason}
                    """
                ).format(
                    mentions=mentions,
                    were=were,
                    until_datetime=until_datetime,
                    with_reason=with_reason,
                )
            )

        if len(failed) > 0:
            mentions = format_list_of_members(failed)
            message_parts.append(f"I failed to tempmute {mentions}")

        await ctx.send("\n".join(message_parts))

    @command(cls=Greedy1Command)
    @only_mentions_users(True)
    async def mute(
        self, ctx: Context, members: Greedy[Member], *, reason: Optional[str]
    ):
        muted = []
        failed = []

        logging.info(f"{ctx.author} used mute with reason {reason}")
        for member in members:
            try:
                await member.add_roles(self.mute_role, reason=reason)
                add_moderation_history_item(
                    member, ModerationAction.MUTE, reason, ctx.author
                )
                logging.info(f"Muted {member}")
                muted.append(member)
            except HTTPException:
                logging.info(f"Failed to mute {member}")
                failed.append(member)

        message_parts = []

        if len(muted) > 0:
            mentions = format_list_of_members(failed)
            were = "were" if len(muted) > 1 else "was"
            with_reason = (
                "with no reason given"
                if reason is None
                else f"with the reason \n> {reason}"
            )
            message_parts.append(
                dedent(
                    """
                    :speaker: **MUTED** :speaker:
                    {mentions} {were} muted {with_reason}
                    """
                ).format(mentions=mentions, were=were, with_reason=with_reason)
            )

        if len(failed) > 0:
            mentions = format_list_of_members(failed)
            message_parts.append(f"I failed to mute {mentions}")

        await ctx.send("\n".join(message_parts))

    @command(cls=Greedy1Command)
    @only_mentions_users(True)
    async def unmute(
        self, ctx: Context, members: Greedy[Member], *, reason: Optional[str]
    ):
        muted = []
        failed = []

        logging.info(f"{ctx.author} used unmute with reason {reason}")
        for member in members:
            try:
                await member.remove_roles(self.mute_role, reason=reason)
                add_moderation_history_item(
                    member, ModerationAction.UNMUTE, reason, ctx.author
                )
                logging.info(f"Unmuted {member}")
                muted.append(member)
            except HTTPException:
                logging.info(f"Failed to unmute {member}")
                failed.append(member)

        message_parts = []

        if len(muted) > 0:
            mentions = format_list_of_members(failed)
            were = "were" if len(muted) > 1 else "was"
            with_reason = (
                "with no reason given"
                if reason is None
                else f"with the reason \n> {reason}"
            )
            message_parts.append(
                dedent(
                    f"""
                            :speaker: **UNMUTED** :speaker:
                            {mentions} {were} unmuted {with_reason}
                            """
                )
            )

        if len(failed) > 0:
            mentions = format_list_of_members(failed)
            message_parts.append(f"I failed to unmute {mentions}")

        await ctx.send("\n".join(message_parts))

    @group(cls=Greedy1Group, invoke_without_command=True)
    @only_mentions_users(True)
    async def warn(
        self, ctx: Context, members: Greedy[Member], *, reason: Optional[str]
    ):
        warned = []
        failed = []

        logging.info(f"{ctx.author} used warn with reason {reason}")
        for member in members:
            try:
                with_reason = (
                    "with no reason given."
                    if reason is None
                    else f"with the following reason: \n> {reason}"
                )
                warning = dedent(
                    """
                    :warning: **WARNING** :warning:
                    You have been warned in UWCS {with_reason}
                    """
                ).format(with_reason=with_reason)
                # Get our DMs with the user or make new ones if they don't exist
                channel = member.dm_channel or await member.create_dm()
                await channel.send(warning)
                add_moderation_history_item(
                    member, ModerationAction.WARN, reason, ctx.author
                )
                logging.info(f"Warned {member}")
                warned.append(member)
            except HTTPException:
                logging.info(f"Failed to warn {member}")
                failed.append(member)

        message_parts = []

        if len(warned) > 0:
            mentions = format_list_of_members(failed)
            were = "were" if len(warned) > 1 else "was"
            with_reason = (
                "with no reason given"
                if reason is None
                else f"with the reason \n> {reason}"
            )
            message_parts.append(
                dedent(
                    """
                    :warning: **WARNED** :warning:
                    {mentions} {were} warned {with_reason}
                    """
                ).format(mentions=mentions, were=were, with_reason=with_reason)
            )

        if len(failed) > 0:
            mentions = format_list_of_members(failed)
            message_parts.append(f"I failed to warn {mentions}")

        await ctx.send("\n".join(message_parts))

    @warn.command()
    async def show(self, ctx: Context, member: Member):
        # First we need to find the database id of the user
        db_user_id = get_database_user(member).id

        # Don't show any warnings that have been removed
        removed_warnings = db_session.query(ModerationHistory.linked_item).filter(
            ModerationHistory.action == ModerationAction.REMOVE_WARN,
            ModerationHistory.user_id == db_user_id,
        )

        # Get the rest of the warnings
        warnings = (
            db_session.query(ModerationHistory)
            .filter(
                ModerationHistory.user_id == db_user_id,
                ModerationHistory.action == ModerationAction.WARN,
                ModerationHistory.id.notin_(removed_warnings),
            )
            .all()
        )
        if any(warnings):

            def format_warning(warning: ModerationHistory):
                moderator = (
                    db_session.query(models.User)
                    .filter(models.User.id == warning.moderator_id)
                    .one_or_none()
                    .username
                )
                date = humanize.naturaldate(warning.timestamp)
                with_reason = (
                    "with no reason provided"
                    if warning.reason is None
                    else f"with reason: {warning.reason}"
                )
                return f" • Warning {warning.id}, issued by {moderator} {date} {with_reason}"

            message_parts = ["The following warnings have been issued:"] + [
                format_warning(w) for w in warnings
            ]
            await ctx.send("\n".join(message_parts))
        else:
            await ctx.send(f"No warnings have been issued for {member.mention}")

    @warn.command()
    async def remove(
        self, ctx: Context, member: Member, warn_id: int, *, reason: Optional[str]
    ):
        valid = (
            db_session.query(ModerationHistory)
            .filter(
                ModerationHistory.id == warn_id,
                ModerationHistory.action == ModerationAction.WARN,
            )
            .count()
            == 1
        )
        if valid:
            add_moderation_history_item(
                member,
                ModerationAction.REMOVE_WARN,
                reason,
                ctx.author,
                linked_item=warn_id,
            )
            await ctx.message.add_reaction(self.emoji["yes"])
        else:
            await ctx.message.add_reaction(self.emoji["what"])

    @command(cls=Greedy1Command)
    @only_mentions_users(True)
    async def kick(
        self, ctx: Context, members: Greedy[Member], *, reason: Optional[str]
    ):
        kicked = []
        failed = []

        logging.info(f"{ctx.author} used kick")
        for member in members:
            try:
                await member.kick(reason=reason)
                add_moderation_history_item(
                    member, ModerationAction.KICK, reason, ctx.author
                )
                logging.info(f"Kicked {member}")
                kicked.append(member)
            except HTTPException:
                logging.warning(f"Failed to kick {member}")
                failed.append(member)

        message_parts = []

        if len(kicked) > 0:
            mentions = format_list_of_members(failed, ping=False)
            with_reason = (
                "with no reason given"
                if reason is None
                else f"with the reason \n> {reason}"
            )
            were = "were" if len(kicked) > 1 else "was"

            message_parts.append(
                dedent(
                    """
                    :door: **KICKED** :door:
                    {mentions} {were} kicked {with_reason}
                    """
                ).format(mentions=mentions, were=were, with_reason=with_reason)
            )

        if len(failed) > 0:
            mentions = format_list_of_members(failed)
            message_parts.append(f"I failed to kick {mentions}")

        await ctx.send("\n".join(message_parts))

    @command(cls=Greedy1Command)
    @only_mentions_users(True)
    async def tempban(
        self,
        ctx: Context,
        members: Greedy[Member],
        until: DateTimeConverter,
        delete_days: Optional[int] = 0,
        *,
        reason: Optional[str],
    ):
        banned = []
        failed = []

        logging.info(f"{ctx.author} used tempban with reason {reason} until {until}")
        for member in members:
            try:
                await member.ban(reason=reason, delete_message_days=delete_days)
                add_moderation_history_item(
                    member, ModerationAction.TEMPBAN, reason, ctx.author, until
                )
                logging.info(f"Tempbanned {member}")
                banned.append(member)
            except HTTPException:
                logging.error(f"Failed to tempban {member}")
                failed.append(member)

        message_parts = []

        if len(banned) > 0:
            mentions = format_list_of_members(failed, ping=False)
            were = "were" if len(banned) > 1 else "was"
            until_datetime = f"until {humanize.naturaltime(until)} (a duration of {humanize.precisedelta(until - datetime.now())})"
            with_reason = (
                "with no reason given."
                if reason is None
                else f"with the reason \n> {reason}"
            )
            messages_deleted = (
                "No messages were deleted."
                if delete_days == 0
                else f"Messages sent in the last {delete_days} day{'s' if delete_days != 1 else ''} were deleted."
            )
            message_parts.append(
                dedent(
                    """
                :hammer: **TEMPBANNED** :hammer:
                {mentions} {were} tempbanned {until_datetime} {with_reason}
                {messages_deleted}
                """
                ).format(
                    mentions=mentions,
                    were=were,
                    until_datetime=until_datetime,
                    with_reason=with_reason,
                    messages_deleted=messages_deleted,
                )
            )

        if len(failed) > 0:
            mentions = format_list_of_members(failed)
            message_parts.append(f"I failed to tempban {mentions}")

        await ctx.send("\n".join(message_parts))

    @command(cls=Greedy1Command)
    @only_mentions_users(True)
    async def ban(
        self,
        ctx: Context,
        members: Greedy[Member],
        delete_days: Optional[int] = 0,
        *,
        reason: Optional[str],
    ):
        banned = []
        failed = []

        logging.info(f"{ctx.author} used ban with reason {reason}")
        for member in members:
            try:
                await member.ban(reason=reason, delete_message_days=delete_days)
                add_moderation_history_item(
                    member, ModerationAction.BAN, reason, ctx.author
                )
                logging.info(f"Banned {member}")
                banned.append(member)
            except HTTPException:
                logging.error(f"Failed to ban {member}")
                failed.append(member)

        message_parts = []

        if len(banned) > 0:
            mentions = format_list_of_members(failed, ping=False)
            were = "were" if len(banned) > 1 else "was"
            with_reason = (
                "with no reason given."
                if reason is None
                else f"with the reason\n> {reason}"
            )
            messages_deleted = (
                "No messages were deleted."
                if delete_days == 0
                else f"Messages sent in the last {delete_days} day{'s' if delete_days != 1 else ''} were deleted."
            )
            message_parts.append(
                dedent(
                    """
                :hammer: **BANNED** :hammer:
                {mentions} {were} banned {with_reason}
                {messages_deleted}
                """
                ).format(
                    mentions=mentions,
                    were=were,
                    with_reason=with_reason,
                    messages_deleted=messages_deleted,
                )
            )

        if len(failed) > 0:
            mentions = format_list_of_members(failed)
            message_parts.append(f"I failed to ban {mentions}")

        await ctx.send("\n".join(message_parts))

    @command(cls=Greedy1Command)
    async def unban(self, ctx: Context, users: Greedy[User], *, reason: Optional[str]):
        unbanned = []
        failed = []

        for user in users:
            try:
                await self.uwcs_guild.unban(user, reason=reason)
                add_moderation_history_item(
                    user, ModerationAction.UNBAN, reason, ctx.author
                )

                logging.info(f"Unbanned {user}")
                unbanned.append(user)
            except HTTPException:
                logging.info(f"Failed to unban {user}")
                failed.append(user)

        message_parts = []

        logging.info(f"{ctx.author} used unban")
        if len(unbanned) > 0:
            mentions = format_list_of_members(unbanned, ping=False)
            with_reason = (
                "with no reason given"
                if reason is None
                else f"with the reason \n> {reason}"
            )
            were = "were" if len(unbanned) > 1 else "was"

            message_parts.append(
                dedent(
                    """
                :dove: **UNBANNED** :dove:
                {mentions} {were} unbanned {with_reason}
                """
                ).format(mentions=mentions, were=were, with_reason=with_reason)
            )

        if len(failed) > 0:
            mentions = format_list([str(user) for user in unbanned])
            message_parts.append(f"I failed to unban {mentions}")

        await ctx.send("\n".join(message_parts))

    @command()
    async def purge(
        self, ctx: Context, number_messages: int, channel: Optional[TextChannel]
    ):
        if channel is None:
            channel = ctx.channel

        # Add 1 to account for the message that was sent to trigger the purge, if the channel is this channel
        this_channel = channel == ctx.channel
        offset = 1 if this_channel else 0
        try:
            await channel.purge(
                check=lambda _: True, limit=number_messages + offset, bulk=True
            )
            if not this_channel:
                await ctx.message.add_reaction(self.emoji["yes"])
            logging.info(
                f"{ctx.author} purged the most recent {number_messages} messages from {channel}"
            )
        except HTTPException:
            await ctx.message.add_reaction(self.emoji["warn"])
            logging.info(
                f"{ctx.author} failed to purge the most recent {number_messages} messages from {channel}"
            )


def setup(bot: Bot):
    bot.add_cog(Moderation(bot))
