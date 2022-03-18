import sqlite3
from typing import Tuple, List

import asyncio
import discord
import sqlalchemy
from discord import AllowedMentions
from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content, CommandInvokeError
from discord.ext.commands.errors import DiscordException, CommandError
from sqlalchemy.exc import SQLAlchemyError

from utils import get_name_string
from voting.discord_interfaces.discord_base import discord_base, Choice
from voting.emoji_list import default_emojis
from voting.splitutils import split_args

LONG_HELP_TEXT = """
Allows running of various types of votes: FPTP, STV, etc. (WIP)
"""

SHORT_HELP_TEXT = """Allows running of various types of votes"""


class Vote(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def vote(self, ctx: Context):
        if not ctx.invoked_subcommand:
            await ctx.send("Subcommand not found")

    @vote.command(help="Run basic poll with given options, votes are visible. Provide options as new-line, semi-colon, comma or space separated options, the first will be taken as the title. If you wish to use a separator in an option, escape it with a backslash `\\`.",
                  brief="Runs basic poll with visible votes. Can use `\\n`, `;`, `,` or ` ` separators. Escape with `\\`",
                  aliases=["quick", "visible"],
                  usage="<title>; [<option 1>; <option 2>; [...]]")
    async def basic(self, ctx: Context, *args: clean_content):
        # noinspection PyTypeChecker
        choices = split_args(" ".join(args))
        await discord_base.create_vote(ctx, choices)


    async def cog_command_error(self, ctx: Context, error):
        if isinstance(error, CommandInvokeError):
            if isinstance(error.original, sqlite3.Error): raise error.original
            if isinstance(error.original, SQLAlchemyError): raise error.original
            err_msg = str(error.original)
        elif isinstance(error, CommandError):
            err_msg = str(error)
        else: raise error
        msg = await ctx.send("Error: " + err_msg)
        await msg.delete(delay=10)



def setup(bot: Bot):
    bot.add_cog(Vote(bot))
