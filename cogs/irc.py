from discord import Message
from discord.ext.commands import Bot, Cog

from utils.utils import user_is_irc_bot


class Irc(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: Message):
        # allow irc users to use commands by altering content to remove the nick before sending for command processing
        # note that clean_content is *not* altered and everything relies on this fact for it to work without having to go back and lookup the message in the db
        # if message.content.startswith("**<"): # <-- FOR TESTING
        if user_is_irc_bot(message):
            # Search for first "> " and strip the message from there (Since irc nicks cant have <, > in them
            idx = message.content.find(">** ")
            idx += 4
            message.content = message.content[idx:]

            ctx = await self.bot.get_context(message)
            await self.bot.invoke(ctx)


def setup(bot: Bot):
    bot.add_cog(Irc(bot))
