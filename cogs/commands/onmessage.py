from re import search, sub

from discord import Message
from discord.abc import GuildChannel
from discord.ext import commands
from discord.ext.commands import Bot, Cog


class OnMessage(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: Message):
        if isinstance(message.channel, GuildChannel):
            # Get all specified command prefixes for the bot
            command_prefixes = self.bot.command_prefix(self.bot, message)
            if not any(
                message.content.startswith(prefix) for prefix in command_prefixes
            ):
                await self.thanks(message)
                await self.scan_replace(
                    message, r"https?://(twitter\.com|x\.com)", "https://fxtwitter.com"
                )
                await self.scan_replace(
                    message,
                    r"https?://(?:old\.|www\.)?reddit\.com",
                    "https://rxddit.com",
                )
                await self.scan_replace(
                    message, r"https?://www\.instagram\.com", "https://uuinstagram.com"
                )

    async def thanks(self, message: Message):
        # to whoever sees this, you're welcome for the not having a fuck off massive indented if
        if message.author.id == self.bot.user.id:
            # dont thank itself
            return
        # Get the previous message (list comprehension my beloved)
        # previous_message = [
        #     message async for message in message.channel.history(limit=2)
        # ][1]
        if message.reference and message.reference.message_id:
            # dont thank replies to something that isnt the bot
            replied_message = await message.channel.fetch_message(
                message.reference.message_id
            )
            if replied_message.author.id != self.bot.user.id:
                return
        #elif (
            #previous_message.author.id != self.bot.user.id
            # and "apollo" not in message.content.lower()
        #):
            # can only thank replies to bot
        else:
            return
        thanks = ["thx", "thanks", "thank you", "ty"]
        # only heart if thanks matches word in message
        if not any(
            search(r"\b" + thank + r"\b", message.content.lower()) for thank in thanks
        ):
            return

        return await message.add_reaction("💜")

    async def scan_replace(self, message: Message, regex, replace):
        send_message = ""
        sentance = message.content.replace("\n", " ").split(" ")
        for word in sentance:
            # if any word contains a link replace with replace
            if search(regex, word):
                send_message += "\n" + sub(regex, replace, word)
        # if there is a message to send, send it
        if send_message != "":
            await message.edit(suppress=True)
            await message.reply(send_message)


async def setup(bot: Bot):
    await bot.add_cog(OnMessage(bot))
