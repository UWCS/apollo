from discord import Message
from discord.ext.commands import Bot, Cog

from config import CONFIG


class Irc(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: Message):
        # allow irc users to use commands by altering content to remove the nick before sending for command processing
        # note that clean_content is *not* altered and everything relies on this fact for it to work without having to go back and lookup the message in the db
        # if message.content.startswith("**<"): # <-- FOR TESTING
        if message.author.id == CONFIG["UWCS_DISCORD_BRIDGE_BOT_ID"]:
            # Search for first "> " and strip the message from there (Since irc nicks cant have <, > in them
            idx = message.content.find(">** ")
            idx += 4
            message.content = message.content[idx:]

            await self.bot.process_commands(message)


def setup(bot: Bot):
    bot.add_cog(Irc(bot))
