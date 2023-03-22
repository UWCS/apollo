import logging
from functools import lru_cache
from typing import Optional

import discord
import openai
from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content

from config import CONFIG

LONG_HELP_TEXT = """
Apollo is smarter than you think...
"""

SHORT_HELP_TEXT = LONG_HELP_TEXT


class ChatGPT(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        openai.api_key = CONFIG.OPENAI_API_KEY
        self.model = "gpt-3.5-turbo"
        self.system_prompt = CONFIG.AI_SYSTEM_PROMPT

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def chat(self, ctx: Context, *, message: str):
        message = await clean_content().convert(ctx, message)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": " ".join(message)},  # type: ignore
        ]
        print(f"Making OpenAI request: {messages}")
        response = openai.ChatCompletion.create(model=self.model, messages=messages)
        print(f"OpenAI Response: {response}")
        await ctx.reply(response.choices[0].message.content, allowed_mentions=discord.AllowedMentions.none())  # type: ignore

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        chat_cmd = CONFIG.PREFIX + "chat"
        # Avoid replying to bot or msg that triggers the command anyway
        if message.author.bot or message.content.startswith(CONFIG.PREFIX):
            return

        # Only engage if replying to Apollo, use !chat to trigger otherwise
        previous = await self.fetch_previous(message)
        if not previous.author.id == self.bot.id:
            return

        message_chain = await self.get_message_chain(message)

        if not any(m.content.startswith(chat_cmd) for m in message_chain):
            return

        messages = [dict(role="system", content=self.system_prompt)]

        for msg in message_chain:
            role = "assistant" if msg.author == self.bot.user else "user"
            content = msg.clean_content.removeprefix(chat_cmd)
            messages.append(dict(role=role, content=content))

        logging.debug(f"Making OpenAI request: {messages}")
        response = openai.ChatCompletion.create(model=self.model, messages=messages)
        logging.debug(f"OpenAI Response: {response}")
        return response.choices[0].message.content

    @lru_cache()
    async def get_message_chain(
        self, message: discord.Message
    ) -> list[discord.Message]:
        """
        Traverses a chain of replies to get a thread of chat messages between a user and Apollo.
        """
        if message is None:
            return []
        previous = await self.fetch_previous(message)
        return [message] + self.get_message_chain(previous)

    async def fetch_previous(
        self, message: discord.Message
    ) -> Optional[discord.Message]:
        if message.reference is not None and message.reference.message_id is not None:
            return await message.channel.fetch_message(message.reference.message_id)
        return None


async def setup(bot: Bot):
    await bot.add_cog(ChatGPT(bot))
