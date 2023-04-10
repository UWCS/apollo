#!/usr/bin/env python3
import asyncio
import logging
from typing import Literal, Optional

import discord
from discord import Intents
from discord.ext import commands
from discord.ext.commands import Bot, Context, Greedy, check, errors, when_mentioned_or
from discord_simple_pretty_help import SimplePrettyHelp

from config import CONFIG
from utils.utils import done_react, is_compsoc_exec_in_guild, wait_react

DESCRIPTION = """
Apollo is the Discord bot for the University of Warwick Computing Society, designed to augment the server with a number of utilities and website services.

Apollo is open source and available at: https://github.com/UWCS/apollo. Pull requests are welcome!
"""

# The command extensions to be loaded by the bot
EXTENSIONS = [
    "cogs.commands.counting",
    "cogs.commands.chatgpt",
    "cogs.commands.dalle",
    "cogs.commands.date",
    "cogs.commands.event_sync",
    "cogs.commands.flip",
    "cogs.commands.karma_admin",
    "cogs.commands.karma_blacklist",
    "cogs.commands.karma",
    "cogs.commands.lcalc",
    "cogs.commands.misc",
    "cogs.commands.quotes",
    "cogs.commands.rolemenu",
    "cogs.commands.reminders",
    "cogs.commands.announce",
    "cogs.commands.roll",
    "cogs.commands.roomsearch",
    "cogs.commands.say",
    "cogs.commands.tex",
    "cogs.commands.vote",
    "cogs.commands.widen",
    "cogs.commands.xkcd",
    "cogs.channel_checker",
    "cogs.commands.system",
    "cogs.database",
    "cogs.irc",
    "cogs.parallelism",
    "cogs.welcome",
]


intents = Intents.default()
intents.members = True
intents.message_content = True

bot = Bot(
    command_prefix=when_mentioned_or(CONFIG.PREFIX),
    description=DESCRIPTION,
    intents=intents,
    help_command=SimplePrettyHelp(),
)


@bot.command()
@check(is_compsoc_exec_in_guild)
async def reload_cogs(ctx: Context):
    for extension in EXTENSIONS:
        await bot.reload_extension(extension)
    await ctx.message.add_reaction("✅")


@bot.event
async def on_ready():
    logging.info("Logged in as")
    logging.info(str(bot.user))
    logging.info("------")


async def main():
    logging.basicConfig(
        level=logging.getLevelName(CONFIG.LOG_LEVEL),
        format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("apollo.log"),
            logging.StreamHandler(),
        ],
    )

    async with bot:
        for extension in EXTENSIONS:
            try:
                logging.info(f"Attempting to load extension {extension}")
                await bot.load_extension(extension)
            except Exception as e:
                logging.exception("Failed to load extension {extension}", exc_info=e)
        await bot.start(CONFIG.DISCORD_TOKEN)


@bot.command()
@commands.guild_only()
@check(is_compsoc_exec_in_guild)
@done_react
@wait_react
async def sync(ctx: Context) -> None:
    """
    Syncs slash commands to server
    """
    synced = await ctx.bot.tree.sync()
    await ctx.send(f"Synced {len(synced)} commands globally to the current guild.")


@bot.event
async def on_command_error(ctx: Context, error: Exception):
    # await ctx.message.add_reaction("🚫")
    message = ""
    reraise = None
    # Custom discord parsing error messages
    if isinstance(error, errors.CommandNotFound):
        pass
    elif isinstance(error, errors.NoPrivateMessage):
        message = "Cannot run this command in DMs"
    elif isinstance(error, errors.ExpectedClosingQuoteError):
        message = f"Mismatching quotes, {str(error)}"
    elif isinstance(error, errors.MissingRequiredArgument):
        message = f"Argument {str(error.param.name)} is missing\nUsage: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`"
    elif isinstance(error, discord.Forbidden):
        message = f"Bot does not have permissions to do this. {str(error.text)}"
        reraise = error
    elif hasattr(error, "original"):
        await on_command_error(ctx, error.original)
        return
    elif isinstance(error, errors.CommandError):
        message = str(error)
    else:
        message = f"{error}"
        reraise = error
    if reraise:
        logging.error(reraise, exc_info=True)

    if message:
        await ctx.send(f"**Error:** `{message}`")
    if reraise:
        raise reraise


if __name__ == "__main__":
    asyncio.run(main())
