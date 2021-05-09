from datetime import datetime, timedelta
from pathlib import Path

import yaml
from discord import AuditLogAction, Embed, Guild, Member, Message, User
from discord.ext.commands import Bot, Cog
from humanize import precisedelta
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy_utils import ScalarListException

from config import CONFIG
from models import User, db_session
from utils import pluralise

FOOTER = "ID: {id}"

JOIN_HEAD = "**Member joined**"
JOIN_DESC = """
{ping}
Created {age} ago. {warning}
"""
JOIN_COLOUR = 0x62FFAE

LEAVE_HEAD = "**Member left**"
LEAVE_DESC = """
{ping} joined {age} ago.
"""
LEAVE_COLOUR = 0xFF62A1

BAN_HEAD = "**User was banned**"
BAN_DESC = """
{user} was banned by {source}.
**Reason:** {reason}
"""
BAN_COLOUR = 0xFF0000

UNBAN_HEAD = "**User was unbanned**"
UNBAN_DESC = """
{user} was unbanned by {source}.
"""
UNBAN_COLOUR = 0x00FF00

EDIT_HEAD = "**Message edited in {channel}**"
EDIT_DESC = """
**Before:** {before}
**+After:** {after}

:arrow_right: {link}
"""
EDIT_UNCACHED_DESC = """
_This message was not cached; the original content is unknown._
**+After:** {after}

:arrow_right: {link}
"""
EDIT_COLOUR = 0xF1FF62

DELETE_HEAD = "**Message deleted in {channel}**"
DELETE_DESC = """
{message}
"""
DELETE_COLOUR = 0xFFB562

NAME_HEAD = "**Name changed**"
NAME_DESC = """
**Before:** {before}
**+After:** {after}
"""
NAME_COLOUR = 0xFF62C8

NICKNAME_HEAD = "**Nickname changed**"
NICKNAME_DESC = """
**Before:** {before}
**+After:** {after}
"""
NICKNAME_COLOUR = 0x6278FF

AVATAR_HEAD = "**Avatar changed**"
AVATAR_DESC = """
{ping}
"""
AVATAR_COLOUR = 0x94FF62

ROLE_HEAD = "**Role{plural} added**"
ROLE_DESC = """
{roles}
"""
ROLE_COLOUR = 0x62FFF8

DEROLE_HEAD = "**Role{plural} removed**"
DEROLE_DESC = """
{roles}
"""
DEROLE_COLOUR = 0xFFAB62

DISCRIMINATOR_HEAD = "**Discriminator changed**"
DISCRIMINATOR_DESC = """
**Before:** {before}
**+After:** {after}
"""
DISCRIMINATOR_COLOUR = 0xFBFF62

VOICE_JOIN_HEAD = "**Joined voice channel**"
VOICE_JOIN_DESC = """
{ping} joined {channel}.
"""
VOICE_JOIN_COLOUR = 0x62FF91

VOICE_LEAVE_HEAD = "**Left voice channel**"
VOICE_LEAVE_DESC = """
{ping} left {channel}.
"""
VOICE_LEAVE_COLOUR = 0xFF62AB

VOICE_MOVE_HEAD = "**Changed voice channel**"
VOICE_MOVE_DESC = """
**Before:** {before}
**+After:** {after}
"""
VOICE_MOVE_COLOUR = 0xFFE662


class Logging(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def log_event(
        self, channel, user: User, title, description, colour, thumbnail_url=None
    ):
        embed = Embed(title=title, description=description, colour=colour)
        if user:
            embed.set_author(
                name=user.display_name + "#" + user.discriminator,
                url=Embed.Empty,
                icon_url=user.avatar_url,
            )
            embed.set_footer(text=FOOTER.format(id=user.id))
        embed.timestamp = datetime.utcnow()
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        await channel.send(embed=embed)

    @Cog.listener()
    async def on_member_join(self, member: Member):
        channel = self.bot.get_channel(CONFIG.UWCS_JOIN_LEAVE_LOG_CHANNEL_ID)
        user = self.bot.get_user(member.id)
        age = datetime.now() - user.created_at
        warning = (
            "**:warning: NEW ACCOUNT! :warning:**" if age < timedelta(days=7) else ""
        )
        title = JOIN_HEAD
        description = JOIN_DESC.format(
            ping=user.mention,
            age=precisedelta(age, minimum_unit="hours"),
            warning=warning,
        )
        colour = JOIN_COLOUR
        await self.log_event(channel, user, title, description, colour)

    @Cog.listener()
    async def on_member_remove(self, member: Member):
        channel = self.bot.get_channel(CONFIG.UWCS_JOIN_LEAVE_LOG_CHANNEL_ID)
        user = self.bot.get_user(member.id)
        age = datetime.now() - member.joined_at
        title = LEAVE_HEAD
        description = LEAVE_DESC.format(
            ping=user.mention, age=precisedelta(age, minimum_unit="hours")
        )
        colour = LEAVE_COLOUR
        await self.log_event(channel, user, title, description, colour)

    @Cog.listener()
    async def on_member_ban(self, guild, user: User):
        channel = self.bot.get_channel(CONFIG.UWCS_JOIN_LEAVE_LOG_CHANNEL_ID)
        logs = await guild.audit_logs(limit=1, action=AuditLogAction.ban).flatten()
        logs = logs[0]
        source = logs.user.mention if logs.target == user else None
        reason = logs.reason if logs.target == user else None
        title = BAN_HEAD
        description = BAN_DESC.format(
            user=user.name + "#" + user.discriminator, source=source, reason=reason
        )
        colour = BAN_COLOUR
        await self.log_event(channel, user, title, description, colour)

    @Cog.listener()
    async def on_member_unban(self, guild, user: User):
        channel = self.bot.get_channel(CONFIG.UWCS_JOIN_LEAVE_LOG_CHANNEL_ID)
        logs = await guild.audit_logs(limit=1, action=AuditLogAction.unban).flatten()
        logs = logs[0]
        source = logs.user.mention if logs.target == user else None
        title = UNBAN_HEAD
        description = UNBAN_DESC.format(
            user=user.name + "#" + user.discriminator, source=source
        )
        colour = UNBAN_COLOUR
        await self.log_event(channel, user, title, description, colour)

    @Cog.listener()
    async def on_member_kick(self, guild, user: User):
        channel = self.bot.get_channel(CONFIG.UWCS_JOIN_LEAVE_LOG_CHANNEL_ID)
        logs = await guild.audit_logs(limit=1, action=AuditLogAction.unban).flatten()
        logs = logs[0]
        source = logs.user.mention if logs.target == user else None
        reason = logs.reason if logs.target == user else None
        title = UNBAN_HEAD
        description = UNBAN_DESC.format(
            user=user.name + "#" + user.discriminator, source=source, reason=reason
        )
        colour = UNBAN_COLOUR
        await self.log_event(channel, user, title, description, colour)

    @Cog.listener()
    async def on_message_edit(self, before: Message, after: Message):
        if before.content == after.content:
            return
        channel = self.bot.get_channel(CONFIG.UWCS_MESSAGE_LOG_CHANNEL_ID)
        user = self.bot.get_user(before.author.id)
        title = EDIT_HEAD.format(channel="#" + before.channel.name)
        description = EDIT_DESC.format(
            before=before.content, after=after.content, link=after.jump_url
        )
        colour = EDIT_COLOUR
        await self.log_event(channel, user, title, description, colour)

    @Cog.listener()
    async def on_raw_message_edit(self, payload):
        if payload.cached_message is not None:
            return
        channel = self.bot.get_channel(CONFIG.UWCS_MESSAGE_LOG_CHANNEL_ID)
        message = await self.bot.get_channel(payload.channel_id).fetch_message(
            payload.message_id
        )
        user = self.bot.get_user(message.author.id)
        title = EDIT_HEAD.format(
            channel="#" + self.bot.get_channel(payload.channel_id).name
        )
        description = EDIT_UNCACHED_DESC.format(
            after=message.content, link=message.jump_url
        )
        colour = EDIT_COLOUR
        await self.log_event(channel, user, title, description, colour)

    @Cog.listener()
    async def on_message_delete(self, message: Message):
        channel = self.bot.get_channel(CONFIG.UWCS_MESSAGE_LOG_CHANNEL_ID)
        user = self.bot.get_user(message.author.id)
        title = DELETE_HEAD.format(channel="#" + message.channel.name)
        description = DELETE_DESC.format(ping=user.mention, message=message.content)
        colour = DELETE_COLOUR
        await self.log_event(channel, user, title, description, colour)

    @Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        if before.nick != after.nick:
            await self.on_member_nick(before, after)
        if any(map(lambda role: role not in before.roles, after.roles)):
            await self.on_member_role(before, after)
        if any(map(lambda role: role not in after.roles, before.roles)):
            await self.on_member_derole(before, after)

    async def on_member_nick(self, before: Member, after: Member):
        channel = self.bot.get_channel(CONFIG.UWCS_MEMBER_LOG_CHANNEL_ID)
        user = self.bot.get_user(before.id)
        title = NICKNAME_HEAD
        description = NICKNAME_DESC.format(before=before.nick, after=after.nick)
        colour = NICKNAME_COLOUR
        await self.log_event(channel, user, title, description, colour)

    async def on_member_role(self, before: Member, after: Member):
        channel = self.bot.get_channel(CONFIG.UWCS_MEMBER_LOG_CHANNEL_ID)
        user = self.bot.get_user(before.id)
        roles = [role.mention for role in after.roles if role not in before.roles]
        title = ROLE_HEAD.format(plural="" if len(roles) == 1 else "s")
        description = ROLE_DESC.format(roles=", ".join(roles))
        colour = ROLE_COLOUR
        await self.log_event(channel, user, title, description, colour)

    async def on_member_derole(self, before: Member, after: Member):
        channel = self.bot.get_channel(CONFIG.UWCS_MEMBER_LOG_CHANNEL_ID)
        user = self.bot.get_user(before.id)
        roles = [role.mention for role in before.roles if role not in after.roles]
        title = DEROLE_HEAD.format(plural="" if len(roles) == 1 else "s")
        description = DEROLE_DESC.format(roles=", ".join(roles))
        colour = DEROLE_COLOUR
        await self.log_event(channel, user, title, description, colour)

    @Cog.listener()
    async def on_user_update(self, before: User, after: User):
        if before.name != after.name:
            await self.on_member_name(before, after)
        if before.discriminator != after.discriminator:
            await self.on_member_discriminator(before, after)
        if before.avatar_url != after.avatar_url:
            await self.on_member_avatar(before, after)

    async def on_member_name(self, before: User, after: User):
        channel = self.bot.get_channel(CONFIG.UWCS_MEMBER_LOG_CHANNEL_ID)
        user = after
        title = NAME_HEAD
        description = NAME_DESC.format(before=before.name, after=after.name)
        colour = NAME_COLOUR
        await self.log_event(channel, user, title, description, colour)

    async def on_member_discriminator(self, before: User, after: User):
        channel = self.bot.get_channel(CONFIG.UWCS_MEMBER_LOG_CHANNEL_ID)
        user = after
        title = DISCRIMINATOR_HEAD
        description = DISCRIMINATOR_DESC.format(
            before=before.discriminator, after=after.discriminator
        )
        colour = DISCRIMINATOR_COLOUR
        await self.log_event(channel, user, title, description, colour)

    async def on_member_avatar(self, before: User, after: User):
        channel = self.bot.get_channel(CONFIG.UWCS_MEMBER_LOG_CHANNEL_ID)
        user = after
        title = AVATAR_HEAD
        description = AVATAR_DESC.format(ping=user.mention)
        colour = AVATAR_COLOUR
        await self.log_event(
            channel, user, title, description, colour, thumbnail_url=after.avatar_url
        )

    @Cog.listener()
    async def on_voice_state_update(self, member: Member, before, after):
        if before.channel is None and after.channel is not None:
            await self.on_voice_join(member, before, after)
        elif before.channel is not None and after.channel is None:
            await self.on_voice_leave(member, before, after)
        elif before.channel != after.channel:
            await self.on_voice_move(member, before, after)

    async def on_voice_join(self, member: Member, before, after):
        channel = self.bot.get_channel(CONFIG.UWCS_VOICE_LOG_CHANNEL_ID)
        user = self.bot.get_user(member.id)
        title = VOICE_JOIN_HEAD
        description = VOICE_JOIN_DESC.format(
            ping=user.mention, channel=after.channel.mention
        )
        colour = VOICE_JOIN_COLOUR
        await self.log_event(channel, user, title, description, colour)

    async def on_voice_leave(self, member: Member, before, after):
        channel = self.bot.get_channel(CONFIG.UWCS_VOICE_LOG_CHANNEL_ID)
        user = self.bot.get_user(member.id)
        title = VOICE_LEAVE_HEAD
        description = VOICE_LEAVE_DESC.format(
            ping=user.mention, channel=before.channel.mention
        )
        colour = VOICE_LEAVE_COLOUR
        await self.log_event(channel, user, title, description, colour)

    async def on_voice_move(self, member: Member, before, after):
        channel = self.bot.get_channel(CONFIG.UWCS_VOICE_LOG_CHANNEL_ID)
        user = self.bot.get_user(member.id)
        title = VOICE_MOVE_HEAD
        description = VOICE_MOVE_DESC.format(
            before=before.channel.mention, after=after.channel.mention
        )
        colour = VOICE_MOVE_COLOUR
        await self.log_event(channel, user, title, description, colour)


def setup(bot: Bot):
    bot.add_cog(Logging(bot))
