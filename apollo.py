#!/usr/bin/env python3
from discord import Intents
from discord.ext.commands import Bot, when_mentioned_or

from config import CONFIG

DESCRIPTION = """
Apollo is the Discord bot for the University of Warwick Computing Society, designed to augment the server with a number of utilities and website services.

Apollo is open source and available at: https://github.com/UWCS/apollo. Pull requests are welcome!
"""

# The command extensions to be loaded by the bot
EXTENSIONS = [
    "cogs.commands.karma",
    "cogs.commands.say",
    "cogs.commands.flip",
    "cogs.commands.misc",
    "cogs.commands.admin",
    "cogs.commands.blacklist",
    "cogs.commands.fact",
    "cogs.commands.reminders",
    "cogs.commands.lcalc",
    "cogs.commands.widen",
    "cogs.commands.tex",
    "cogs.welcome",
    "cogs.database",
    "cogs.irc",
]


intents = Intents.default()
intents.members = True

bot = Bot(
    command_prefix=when_mentioned_or("!"), description=DESCRIPTION, intents=intents
)


@bot.event
async def on_ready():
    if CONFIG["BOT_LOGGING"]:
        # TODO: Write this to a logging file?
        print("Logged in as")
        print(str(bot.user))
        print("------")


if __name__ == "__main__":
    for extension in EXTENSIONS:
        try:
            bot.load_extension(extension)
        except Exception as e:
            exc = "{}: {}".format(type(e).__name__, e)
            print("Failed to load extension {}\n{}".format(extension, exc))

    bot.run(CONFIG["DISCORD_TOKEN"])
