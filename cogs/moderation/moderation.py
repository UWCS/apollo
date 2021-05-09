import logging
from textwrap import dedent
from typing import Optional

from discord import HTTPException, Member, TextChannel, User
from discord.ext.commands import Bot, Cog, Context, Greedy, check, command
from discord.utils import get
from sqlalchemy.exc import SQLAlchemyError

import models
from config import CONFIG
from models import ModerationAction, ModerationHistory, db_session
from utils import AdminError, format_list, is_compsoc_exec_in_guild


def add_moderation_history_item(user, action, reason, moderator):

    user_id = db_session.query(models.User).filter(models.User.user_uid == user.id).first().id
    moderator_id = db_session.query(models.User).filter(models.User.user_uid == moderator.id).first().id
    moderation_history = ModerationHistory(
        user_id=user_id,
        action=action,
        reason=reason,
        moderator_id=moderator_id,
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
        self._emoji = None

    @property
    def emoji(self):
        if self._emoji is None:
            self._emoji = {
                "no": get(self.bot.emojis, id=840911865830703124),
                "what": get(self.bot.emojis, id=840917271111008266),
                "warn": get(self.bot.emojis, id=840911836580544512),
                "yes": get(self.bot.emojis, id=840911879886209024),
            }
        return self._emoji

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
        await ctx.message.add_reaction(self.emoji["no"])

    @command()
    @only_mentions_users(True)
    async def ban(
        self,
        ctx: Context,
        members: Greedy[Member],
        delete_days: Optional[int] = 0,
        *,
        reason: Optional[str],
    ):
        if len(members) == 0:
            await ctx.message.add_reaction(self.emoji["what"])
            return

        banned = []
        failed = []

        logging.info(f"{ctx.author} used ban")
        for member in members:
            try:
                await member.ban(reason=reason, delete_message_days=delete_days)
                add_moderation_history_item(member, ModerationAction.BAN, reason, ctx.author)
                logging.info(f"Banned {member}")
                banned.append(member)
            except HTTPException:
                logging.error(f"Failed to ban {member}")
                failed.append(member)

        message_parts = []

        if len(banned) > 0:
            mentions = format_list([member.mention for member in banned])
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
            mentions = format_list([member.mention for member in failed])
            message_parts.append(f"I failed to ban {mentions}")

        await ctx.send("\n".join(message_parts))

    @command()
    async def unban(self, ctx: Context, users: Greedy[User], *, reason: Optional[str]):
        if len(users) == 0:
            await ctx.message.add_reaction(self.emoji["what"])

        unbanned = []
        failed = []

        guild = self.bot.get_guild(CONFIG.UWCS_DISCORD_ID)
        for user in users:
            try:
                await guild.unban(user, reason=reason)
                add_moderation_history_item(user, ModerationAction.UNBAN, reason, ctx.author)

                logging.info(f"Unbanned {user}")
                unbanned.append(user)
            except HTTPException:
                logging.info(f"Failed to unban {user}")
                failed.append(user)

        message_parts = []

        logging.info(f"{ctx.author} used unban")
        if len(unbanned) > 0:
            mentions = format_list([str(user) for user in unbanned])
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
    @only_mentions_users(True)
    async def kick(
        self, ctx: Context, members: Greedy[Member], *, reason: Optional[str]
    ):
        if len(members) == 0:
            await ctx.message.add_reaction(self.emoji["what"])

        kicked = []
        failed = []

        logging.info(f"{ctx.author} used kick")
        for member in members:
            try:
                await member.kick(reason=reason)
                add_moderation_history_item(member, ModerationAction.KICK, reason, ctx.author)
                logging.info(f"Kicked {member}")
                kicked.append(member)
            except HTTPException:
                logging.warning(f"Failed to kick {member}")
                failed.append(member)

        message_parts = []

        if len(kicked) > 0:
            mentions = format_list([member.mention for member in kicked])
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
            mentions = format_list([member.mention for member in failed])
            message_parts.append(f"I failed to kick {mentions}")

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
