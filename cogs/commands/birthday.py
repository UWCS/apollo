from datetime import datetime

from discord.ext import commands
from discord.ext.commands import Bot, Context
from pytz import timezone, utc
from sqlalchemy.exc import SQLAlchemyError

from config import CONFIG
from models import db_session
from models.birthday import Birthday as db_Birthday  # avoid name clash

LONG_HELP_TEXT = """
Hapy birthday!!!!

As is tradtion, wish our dear lord chancellor of the computer a happy birthday
"""

SHORT_HELP_TEXT = "Hapy birthday!!!!"


class Birthday(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        recent = db_session.query(db_Birthday).order_by(db_Birthday.date.desc()).first()
        if recent:  # store the most recent birthday
            self.date = recent.date
            self.age = recent.age
        else:  # if there is no birthday, initialise
            self.date = utc.localize(datetime(1970, 1, 1)).astimezone(
                timezone("Europe/London")
            )
            self.age = 0

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def birthday(self, ctx: Context):
        current_date = utc.localize(datetime.now()).astimezone(
            timezone("Europe/London")
        )
        if current_date.date() <= self.date.date():
            return await ctx.reply(
                "I'm sorry but our lord chancellor has already been wished a happy birthday today"
            )
        self.date = current_date
        self.age += 1
        borth = db_Birthday(date=self.date, age=self.age)
        db_session.add(borth)
        db_session.commit()
        await ctx.reply(
            f"Happy birthday!!!! <@{CONFIG.LORD_CHANCELLOR_ID}>, you are now {self.age}"
        )

    @commands.hybrid_command(help="get current age", brief="get current age")
    async def age(self, ctx: Context):
        name = self.bot.get_user(CONFIG.LORD_CHANCELLOR_ID).name
        await ctx.reply(f"{name} is {self.age}")


async def setup(bot: Bot):
    await bot.add_cog(Birthday(bot))
