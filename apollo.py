#!/usr/bin/env python3
import logging

from discord import Intents
from discord.ext.commands import Bot, Context, check, when_mentioned_or

from config import CONFIG
from utils.utils import is_compsoc_exec_in_guild

DESCRIPTION = """
Apollo is the Discord bot for the University of Warwick Computing Society, designed to augment the server with a number of utilities and website services.

Apollo is open source and available at: https://github.com/UWCS/apollo. Pull requests are welcome!
"""

# The command extensions to be loaded by the bot
EXTENSIONS = [
    "cogs.commands.admin",
    "cogs.commands.blacklist",
    "cogs.commands.counting",
    "cogs.commands.date",
    "cogs.commands.flip",
    "cogs.commands.karma",
    "cogs.commands.lcalc",
    "cogs.commands.misc",
    "cogs.commands.quotes",
    "cogs.commands.reminders",
    "cogs.commands.roll",
    "cogs.commands.say",
    "cogs.commands.tex",
    "cogs.commands.widen",
    "cogs.database",
    "cogs.irc",
    "cogs.parallelism",
    "cogs.welcome",
]


intents = Intents.default()
intents.members = True

bot = Bot(
    command_prefix=when_mentioned_or("!"), description=DESCRIPTION, intents=intents
)


@bot.command()
@check(is_compsoc_exec_in_guild)
async def reload_cogs(ctx: Context):
    for extension in EXTENSIONS:
        bot.reload_extension(extension)
    await ctx.message.add_reaction("✅")


@bot.event
async def on_ready():
    if CONFIG.BOT_LOGGING:
        logging.info("Logged in as")
        logging.info(str(bot.user))
        logging.info("------")


def main():
    if CONFIG.BOT_LOGGING:
        logging.basicConfig(level=logging.WARNING)
    for extension in EXTENSIONS:
        try:
            logging.info(f"Attempting to load extension {extension}")
            bot.load_extension(extension)
        except Exception as e:
            exc = f"{type(e).__name__}: {e.with_traceback()}"
            logging.error(f"Failed to load extension {extension}\n{exc}")
    bot.run(CONFIG.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
