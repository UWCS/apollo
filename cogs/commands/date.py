import random
from datetime import date

from discord.ext import commands
from discord.ext.commands import Bot, Context

DATE_HELP_TEXT = """Ask the bot what the date is."""
DAY_HELP_TEXT = """Ask the bot what the day is."""


class Date(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(help=DATE_HELP_TEXT, brief=DATE_HELP_TEXT)
    async def date(self, ctx: Context):
        """99% of the time return the date. 1% of the time (if I can do maths) returns a picture of a date"""
        output = date.today()
        randno = random.random()
        if randno <= 0.01:
            await ctx.send(
                "https://solidstarts.com/wp-content/uploads/dates_edited-scaled.jpg"
            )
        else:
            await ctx.send(output.strftime("%A %d %B %Y"))

    @commands.command(help=DAY_HELP_TEXT, brief=DAY_HELP_TEXT)
    async def day(self, ctx: Context):
        """Return the current day"""
        output = date.today()
        await ctx.send(output.strftime("%A"))


async def setup(bot: Bot):
    await bot.add_cog(Date(bot))
