from datetime import datetime

from discord import User
from discord.ext import commands
from discord.ext.commands import Bot, Context
from pytz import timezone, utc

from config import CONFIG
from models import db_session
from models.birthday import Birthday as db_Birthday  # avoid name clash

LONG_HELP_TEXT = """
Hapy birthday!!!!

As is tradtion, wish our dear lord chancellor of the computer a happy birthday
"""


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

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief="HAPPY BIRTHDAY!!!!")
    async def birthday(self, ctx: Context):
        """Adds 1 to the age of the Lord Chancellor and wishes them a happy birthday"""
        current_date = utc.localize(datetime.now()).astimezone(
            timezone("Europe/London")
        )  # gets the current date
        if current_date.date() <= self.date.date():
            return await ctx.reply(
                "I'm sorry but our high and gracious Lord Chancellor has already been wished a happy birthday today"
            )  # cannot wish happy birthday twice in one day
        self.date = current_date
        self.age += 1
        borth = db_Birthday(date=self.date, age=self.age, user_id=ctx.author.id)
        db_session.add(borth)
        db_session.commit()
        # update the database
        await ctx.reply(
            f"Happy birthday!!!! <@{CONFIG.LORD_CHANCELLOR_ID}>, you are now {self.age}"
        )

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief="Lord Chancellor age")
    async def age(self, ctx: Context):
        """Get the current age of the Lord Chancellor"""
        name = self.bot.get_user(CONFIG.LORD_CHANCELLOR_ID).name
        await ctx.reply(f"{name} is {self.age}")

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief="User happy birthday count")
    async def birthdayUser(self, ctx: Context, user: User):
        """How many times has someone wished the Lord Chancellor a happy birthday?"""
        num = (
            db_session.query(db_Birthday).filter(db_Birthday.user_id == user.id).count()
        )
        await ctx.reply(
            f"{user.name} has wished the Lord Chancellor a happy birthday {num} times"
        )


async def setup(bot: Bot):
    await bot.add_cog(Birthday(bot))
