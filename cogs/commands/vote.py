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

from models import DiscordVote, db_session
from utils import get_name_string
from voting.discord_interfaces.discord_base import discord_base, Choice
from voting.emoji_list import default_emojis
from voting.splitutils import split_args
from voting.utils import get_interface, vote_interfaces

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
        print(choices)
        await discord_base.create_vote(ctx, choices)



    @commands.Cog.listener()
    @commands.guild_only()
    async def on_raw_reaction_add(self, reaction: discord.RawReactionActionEvent):
        if reaction.user_id == self.bot.user.id: return

        interface, vote_msg_obj = get_interface(reaction.message_id)
        if interface is None: return
        await interface.react_add(
            vote_msg_obj,
            reaction.user_id,
            str(reaction.emoji))

    @commands.Cog.listener()
    @commands.guild_only()
    async def on_raw_reaction_remove(self, reaction: discord.RawReactionActionEvent):
        if reaction.user_id == self.bot.user.id: return

        interface, vote_msg_obj = get_interface(reaction.message_id)
        if interface is None: return
        await interface.react_remove(
            vote_msg_obj,
            reaction.user_id,
            str(reaction.emoji))


    async def cog_command_error(self, ctx: Context, error):
        if isinstance(error, CommandInvokeError):
            if isinstance(error.original, sqlite3.Error): raise error.original
            if isinstance(error.original, SQLAlchemyError): raise error.original
            err_msg = str(error.original)
        elif isinstance(error, CommandError):
            err_msg = str(error)
        else: raise error
        msg = await ctx.send("Error: " + err_msg)
        # await msg.delete(delay=10)
        raise error



def setup(bot: Bot):
    bot.add_cog(Vote(bot))
    for dci in vote_interfaces.values():
        dci.bot = bot
