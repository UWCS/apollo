import re
from datetime import datetime

import requests
from discord.abc import PrivateChannel
from discord.ext import commands
from discord.ext.commands import CommandError, Context, check, Bot, clean_content

from config import CONFIG
from models import User, db_session

LONG_HELP_TEXT = """
Make the bot repeat after you.
"""

SHORT_HELP_TEXT = """Make the bot repeat after you."""

class Say:
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def say(self, ctx: Context, *message: clean_content):
       await ctx.send(" ".join([x.lstrip('@') for x in message])) 

def setup(bot: Bot):
    bot.add_cog(Say(bot))
