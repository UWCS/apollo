import logging
from typing import Optional

import discord
import openai
from cache import AsyncLRU
from discord import AllowedMentions
from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content

from config import CONFIG

LONG_HELP_TEXT = """
Apollo is smarter than you think...
"""

SHORT_HELP_TEXT = LONG_HELP_TEXT

mentions = AllowedMentions(everyone=False, users=False, roles=False, replied_user=True)

class ChatGPT(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        openai.api_key = CONFIG.OPENAI_API_KEY
        self.model = "gpt-3.5-turbo"
        self.system_prompt = CONFIG.AI_SYSTEM_PROMPT

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def chat(self, ctx: Context, *, message: str):
        response = await self.dispatch_api(ctx.message, False)
        if response:
            await ctx.reply(response, allowed_mentions=mentions)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Avoid replying to bot or msg that triggers the command anyway
        if message.author.bot or message.content.startswith(CONFIG.PREFIX):
            return

        # Only engage if replying to Apollo, use !chat to trigger otherwise
        previous = await self.fetch_previous(message)
        if not previous or not previous.author.id == self.bot.user.id:
            return

        response = await self.dispatch_api(message)
        await message.reply(response, allowed_mentions=mentions)

    async def dispatch_api(
        self, message: discord.Message, from_msg: bool = False
    ) -> Optional[str]:
        chat_cmd = CONFIG.PREFIX + "chat "
        message_chain = await self.get_message_chain(message)

        is_cmd = lambda m: m.content.startswith(chat_cmd) or (
            m.interaction and m.interaction.name == "chat"
        )
        if from_msg and not any(map(is_cmd, message_chain)):
            return None

        messages = [dict(role="system", content=self.system_prompt)]

        for msg in message_chain:
            role = "assistant" if msg.author == self.bot.user else "user"
            content = msg.clean_content.removeprefix(chat_cmd)
            messages.append(dict(role=role, content=content))

        logging.info(f"Making OpenAI request: {messages}")
        response = openai.ChatCompletion.create(model=self.model, messages=messages)
        logging.info(f"OpenAI Response: {response}")
        return response.choices[0].message.content

    @AsyncLRU()
    async def get_message_chain(
        self, message: discord.Message
    ) -> list[discord.Message]:
        """
        Traverses a chain of replies to get a thread of chat messages between a user and Apollo.
        """
        if message is None:
            return []
        previous = await self.fetch_previous(message)
        return (await self.get_message_chain(previous)) + [message]

    async def fetch_previous(
        self, message: discord.Message
    ) -> Optional[discord.Message]:
        if message.reference is not None and message.reference.message_id is not None:
            return await message.channel.fetch_message(message.reference.message_id)
        return None


async def setup(bot: Bot):
    await bot.add_cog(ChatGPT(bot))
