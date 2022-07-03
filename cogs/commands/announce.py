import asyncio
import logging
from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import Bot, Context, MissingPermissions
from humanize import precisedelta
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy_utils import ScalarListException

from config import CONFIG
from models import Announcement, db_session
from utils import DateTimeConverter, get_database_user, get_name_string, user_is_irc_bot, is_compsoc_exec_in_guild

from utils.announce_utils import generate_announcement, confirmation

LONG_HELP_TEXT = """
Add announcements for yourself or remove the last one you added.
"""
SHORT_HELP_TEXT = """Add or remove announcements."""


def get_user_name(irc_name, user_uid, bot):
    name, avatar = None, None
    if irc_name:
        name = irc_name
    else:
        author_uid = user_uid
        author = bot.get_user(author_uid)
        name = author.name
        avatar = author.avatar_url
    return name, avatar

async def get_webhook(channel):
    try:
        webhooks = await channel.webhooks()
        webhook = next((w for w in webhooks if w.name == "Apollo Announcements"), None)
        if webhook is None:
            webhook = await channel.create_webhook(name="Apollo Announcements")
        return webhook
    except MissingPermissions:
        return None


class Announcements(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.bot.loop.create_task(announcement_check(self.bot))

    @commands.group(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def announcement(self, ctx: Context):
        if not ctx.invoked_subcommand:
            await ctx.send("Subcommand not found.")

    @announcement.command(
        help='Add a announcement, format "yyyy-mm-dd hh:mm" or "mm-dd hh:mm" or hh:mm:ss or hh:mm or xdxhxmxs or any ordered combination of the last format, then finally your announcement (rest of discord message).'
    )
    async def add(self, ctx: Context, channel: discord.TextChannel, trigger_time: DateTimeConverter, *, announcement_content: str):
        # Function very similar to reminders
        if not await is_compsoc_exec_in_guild(ctx):
            return await ctx.send("Must be exec to use this command.")

        now = datetime.now()
        if not trigger_time:
            return await ctx.send("Incorrect time format, please see help text.")
        if trigger_time < now:
            return await ctx.send("That time is in the past.")

        result = await self.preview_announcement(ctx, announcement_content, False)
        if not result: return

        # The time is valid and not in the past, add the announcement
        await self.add_announcement(ctx, channel, trigger_time, announcement_content)


    @announcement.command(help='Preview the rendering of a announcement')
    async def preview(self, ctx: Context, *, announcement_content: str):
        await self.preview_announcement(ctx, announcement_content, True)


    async def preview_announcement(self, ctx, announcement_content: str, preview: bool = True):
        channel = ctx.channel
        webhook = await get_webhook(channel)
        messages = await generate_announcement(channel, announcement_content, webhook, ctx.author.name, ctx.author.avatar_url)

        # Function for reaction to interact with message
        async def interact(msg, reaction):
            await msg.delete()
            # If edit or delete, remove old messages
            if str(reaction) in {"❌", "✏️"}:
                for ann_msg in messages:
                    await ann_msg.delete()

                if str(reaction) == "❌":
                    await ctx.send("Announcement cancelled")
                if str(reaction) == "✏️":
                    edit_msg: discord.Message = await ctx.fetch_message(ctx.message.id)
                    await ctx.bot.process_commands(edit_msg)
                return

            if preview:
                await ctx.send(f"Preview complete. Send this message with\n`!announcement add #announcements 10s \n{announcement_content}`")

            return True

        async def timeout(msg):
            await msg.delete()
            await ctx.send(f"**Timeout.** Restart posting with: `!announcement preview {announcement_content}`")
            for ann_msg in messages:
                await ann_msg.delete()
            return False

        return await confirmation(ctx, f"Edit Preview",
                           f"  ✅ to {'finalize' if preview else 'schedule announcement'}\n  ✏️ to edit (make changes in source first)\n  ❌ to cancel",
                           ["✅", "✏️", "❌"], interact, timeout, 300)


    async def add_announcement(self, ctx, channel, trigger_time, announcement_content):
        display_name = get_name_string(ctx.message)
        # Set the id to a random value if the author was the bridge bot, since we won't be using it anyway
        # if ctx.message.clean_content.startswith("**<"): <---- FOR TESTING
        if user_is_irc_bot(ctx):
            author_id = 1
            irc_n = display_name
        else:
            author_id = get_database_user(ctx.author).id
            irc_n = None

        trig_at = trigger_time
        trig = False
        playback_ch_id = channel.id
        new_announcement = Announcement(
            user_id=author_id,
            announcement_content=announcement_content,
            trigger_at=trig_at,
            triggered=trig,
            playback_channel_id=playback_ch_id,
            irc_name=irc_n,
        )
        db_session.add(new_announcement)
        try:
            db_session.commit()
            await ctx.send(
                f"Announcement prepared, but note granularity is set at {precisedelta(CONFIG.REMINDER_SEARCH_INTERVAL, minimum_unit='seconds')})."
            )

        except (ScalarListException, SQLAlchemyError) as e:
            db_session.rollback()
            logging.exception(e)
            await ctx.send(f"Something went wrong")


async def announcement_check(bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.now()
        announcements = (
            db_session.query(Announcement)
            .filter(Announcement.trigger_at <= now, Announcement.triggered == False)
            .all()
        )

        for a in announcements:
            channel = bot.get_channel(a.playback_channel_id)
            webhook = await get_webhook(channel)

            name, avatar = get_user_name(a.irc_name, a.user.user_uid, bot)
            message = a.announcement_content
            a.triggered = True
            db_session.commit()

            await generate_announcement(channel, message, webhook, name, avatar)

        await asyncio.sleep(CONFIG.REMINDER_SEARCH_INTERVAL)


def setup(bot: Bot):
    bot.add_cog(Announcements(bot))
