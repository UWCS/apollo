import random
from datetime import date, datetime

from discord.ext import commands
from discord.ext.commands import Bot, Context

from utils import parse_time

DATE_HELP_TEXT = """Ask the bot what the date is."""
DAY_HELP_TEXT = """Ask the bot what the day is."""
TIME_HELP_TEXT = """Ask the bot what the time is."""
TIMESTAMP_HELP_TEXT = """Get the Discord timestamp of a time"""


class Date(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_command(help=DATE_HELP_TEXT, brief=DATE_HELP_TEXT)
    async def date(self, ctx: Context):
        """99% of the time return the date. 1% of the time (if I can do maths) returns a picture of a date"""
        output = datetime.now()
        randno = random.random()
        if randno <= 0.01:
            await ctx.send(
                "https://solidstarts.com/wp-content/uploads/dates_edited-scaled.jpg"
            )
        else:
            await ctx.send(f"<t:{output.timestamp()}:F>")

    @commands.hybrid_command(help=DAY_HELP_TEXT, brief=DAY_HELP_TEXT)
    async def day(self, ctx: Context):
        """Return the current day"""
        output = date.today()
        await ctx.send(output.strftime("%A"))

    @commands.hybrid_command(help=TIME_HELP_TEXT, brief=TIME_HELP_TEXT)
    async def time(self, ctx: Context):
        """Return the current time"""
        output = datetime.now()
        await ctx.send(f"<t:{int(output.timestamp())}:t>")

    @commands.hybrid_command(help=TIME_HELP_TEXT, brief=TIME_HELP_TEXT)
    async def timestamp(self, ctx: Context, when: str):
        """Return the current time"""
        time = parse_time(when)
        timestamp = int(time.timestamp())
        await ctx.send(f"`<t:{timestamp}:R>` -> <t:{timestamp}:R>")

    @commands.hybrid_command(help=TIME_HELP_TEXT, brief=TIME_HELP_TEXT)
    async def timestamps(self, ctx: Context, when: str):
        """Return the current time"""
        time = parse_time(when)
        timestamp = int(time.timestamp())

        await ctx.send(
            f"""**All formats:**
`<t:{timestamp}:d>` -> <t:{timestamp}:d>
`<t:{timestamp}:D>` -> <t:{timestamp}:D>
`<t:{timestamp}:t>` -> <t:{timestamp}:t>
`<t:{timestamp}:T>` -> <t:{timestamp}:T>
`<t:{timestamp}:f>` -> <t:{timestamp}:f>
`<t:{timestamp}:F>` -> <t:{timestamp}:F>
`<t:{timestamp}:R>` -> <t:{timestamp}:R>
"""
        )


async def setup(bot: Bot):
    await bot.add_cog(Date(bot))
