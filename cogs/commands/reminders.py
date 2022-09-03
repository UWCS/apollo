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
from utils import get_database_user, get_name_string, parse_time, user_is_irc_bot

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

    @commands.hybrid_group(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def reminder(self, ctx: Context):
        if not ctx.invoked_subcommand:
            await ctx.send("Subcommand not found.")

    @reminder.command(
        help="Add a reminder, when can be absolute or relative, but place in quotes if multiple words."
    )
    async def add(self, ctx: Context, when: str, *, reminder_content: str):
        trigger_time = parse_time(when)
        display_name = get_name_string(ctx.message)
        if user_is_irc_bot(ctx):
            author_id, irc_n = 1, display_name
        else:
            author_id, irc_n = get_database_user(ctx.author).id, None

        new_reminder = Reminder(
            user_id=author_id,
            reminder_content=reminder_content,
            trigger_at=trigger_time,
            triggered=False,
            playback_channel_id=ctx.message.channel.id,
            irc_name=irc_n,
        )

        result = self.add_base(new_reminder)
        await ctx.send(**result)

    def add_base(self, reminder):
        now = datetime.now()
        if not reminder.trigger_at:
            return {"content": "Incorrect time format, please see help text."}
        elif reminder.trigger_at < now:
            return {"content": "That time is in the past."}

        db_session.add(reminder)
        try:
            db_session.commit()
            gran = precisedelta(CONFIG.REMINDER_SEARCH_INTERVAL, minimum_unit="seconds")
            return {
                "content": f"Reminder prepared for <t:{int(reminder.trigger_at.timestamp())}:R> (granularity is {gran})."
            }
        except (ScalarListException, SQLAlchemyError) as e:
            db_session.rollback()
            logging.exception(e)
            return {"content": f"Something went wrong with the database"}


async def setup(bot: Bot):
    await bot.add_cog(Reminders(bot))
