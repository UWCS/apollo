import asyncio
import logging
from datetime import datetime

from discord.ext import commands
from discord.ext.commands import Bot, Context
from humanize import precisedelta
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy_utils import ScalarListException

from config import CONFIG
from models import Reminder, db_session
from utils import (
    DateTimeConverter,
    get_database_user,
    get_database_user_from_id,
    get_name_string,
    user_is_irc_bot,
)

LONG_HELP_TEXT = """
Add reminders for yourself or remove the last one you added.
"""
SHORT_HELP_TEXT = """Add or remove reminders."""


async def reminder_check(bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.now()
        reminders = (
            db_session.query(Reminder)
            .filter(Reminder.trigger_at <= now, Reminder.triggered == False)  # noqa 712
            .all()
        )
        for r in reminders:
            if r.irc_name:
                display_name = r.irc_name
            else:
                author_uid = r.user.user_uid
                display_name = f"<@{author_uid}>"
            channel = bot.get_channel(r.playback_channel_id)
            message = f"Reminding {display_name}: " + r.reminder_content
            await channel.send(message)
            r.triggered = True
            db_session.commit()

        await asyncio.sleep(CONFIG.REMINDER_SEARCH_INTERVAL)


class Reminders(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.bot.loop.create_task(reminder_check(self.bot))

    @commands.group(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def reminder(self, ctx: Context):
        if not ctx.invoked_subcommand:
            await ctx.send("Subcommand not found.")

    @reminder.command(
        help='Add a reminder, format "yyyy-mm-dd hh:mm" or "mm-dd hh:mm" or hh:mm:ss or hh:mm or xdxhxmxs or any ordered combination of the last format, then finally your reminder (rest of discord message).'
    )
    async def add(
        self, ctx: Context, trigger_time: DateTimeConverter, *, reminder_content: str
    ):
        now = datetime.now()
        if not trigger_time:
            await ctx.send("Incorrect time format, please see help text.")
        elif trigger_time < now:
            await ctx.send("That time is in the past.")
        else:
            # HURRAY the time is valid and not in the past, add the reminder
            display_name = get_name_string(ctx.message)

            # set the id to a random value if the author was the bridge bot, since we wont be using it anyways
            # if ctx.message.clean_content.startswith("**<"): <---- FOR TESTING
            if user_is_irc_bot(ctx):
                author_id = 1
                irc_n = display_name
            else:
                author_id = get_database_user(ctx.author).id
                irc_n = None

            trig_at = trigger_time
            trig = False
            playback_ch_id = ctx.message.channel.id
            new_reminder = Reminder(
                user_id=author_id,
                reminder_content=reminder_content,
                trigger_at=trig_at,
                triggered=trig,
                playback_channel_id=playback_ch_id,
                irc_name=irc_n,
            )
            db_session.add(new_reminder)
            try:
                db_session.commit()
                await ctx.send(
                    f"Thanks {display_name}, I have saved your reminder (but please note that my granularity is set at {precisedelta(CONFIG.REMINDER_SEARCH_INTERVAL, minimum_unit='seconds')})."
                )
            except (ScalarListException, SQLAlchemyError) as e:
                db_session.rollback()
                logging.exception(e)
                await ctx.send(f"Something went wrong")


def setup(bot: Bot):
    bot.add_cog(Reminders(bot))
