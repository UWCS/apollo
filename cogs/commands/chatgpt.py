from functools import lru_cache

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
        if message.content.startswith(CONFIG.PREFIX):
            return

        message_chain = await self.get_message_chain(message)

        if not message_chain[0].content.startswith(chat_cmd):
            return

        messages = [dict(role="system", content=self.system_prompt)]

        for msg in message_chain:
            role = "assistant" if msg.author == self.bot.user else "user"
            content = msg.clean_content.removeprefix(chat_cmd)
            messages.append(dict(role=role, content=content))

        print(f"Making OpenAI request: {messages}")
        response = openai.ChatCompletion.create(model=self.model, messages=messages)
        print(f"OpenAI Response: {response}")
        await message.reply(response.choices[0].message.content)  # type: ignore

    @lru_cache()
    async def get_message_chain(self, message) -> list[discord.Message]:
        """
        Traverses a chain of replies to get a thread of chat messages between a user and Apollo.
        """
        if message.reference is not None and message.reference.message_id is not None:
            # if the reply was a valid reply, fetch it
            previous = await message.channel.fetch_message(message.reference.message_id)
            return await [message] + self.get_message_chain(previous)
        return []


async def setup(bot: Bot):
    await bot.add_cog(ChatGPT(bot))
