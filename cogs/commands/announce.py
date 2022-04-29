import asyncio
import logging
from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import Bot, Context
from humanize import precisedelta
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy_utils import ScalarListException

from config import CONFIG
from models import Announcement, db_session
from utils import DateTimeConverter, get_database_user, get_name_string, user_is_irc_bot, is_compsoc_exec_in_guild

from utils.announce_utils import generate_announcement

LONG_HELP_TEXT = """
Add announcements for yourself or remove the last one you added.
"""
SHORT_HELP_TEXT = """Add or remove announcements."""


async def announcement_check(bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.now()
        announcements = (
            db_session.query(Announcement)
            .filter(Announcement.trigger_at <= now, Announcement.triggered == False)  # noqa 712
            .all()
        )
        for r in announcements:
            if r.irc_name:
                display_name = r.irc_name
            else:
                author_uid = r.user.user_uid
                display_name = f"<@{author_uid}>"
            channel = bot.get_channel(r.playback_channel_id)
            message = r.announcement_content
            r.triggered = True
            db_session.commit()

            await generate_announcement(channel, message)

        await asyncio.sleep(CONFIG.REMINDER_SEARCH_INTERVAL)


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
    async def add(
        self, ctx: Context, channel: discord.TextChannel, trigger_time: DateTimeConverter, *, announcement_content: str
    ):
        if not await is_compsoc_exec_in_guild(ctx):
            await ctx.send("Must be exec to use this command.")
            return

        now = datetime.now()
        if not trigger_time:
            await ctx.send("Incorrect time format, please see help text.")
        elif trigger_time < now:
            await ctx.send("That time is in the past.")
        else:
            # HURRAY the time is valid and not in the past, add the announcement
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
                    f"Announcement prepared, but note granularity is set at {precisedelta(CONFIG.REMINDER_SEARCH_INTERVAL, minimum_unit='seconds')}). \n**Message preview:**"
                )

                await generate_announcement(ctx.channel, announcement_content)

            except (ScalarListException, SQLAlchemyError) as e:
                db_session.rollback()
                logging.exception(e)
                await ctx.send(f"Something went wrong")


def setup(bot: Bot):
    bot.add_cog(Announcements(bot))
