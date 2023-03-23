import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
import openai
from cache import AsyncLRU
from discord import AllowedMentions
from discord.ext import commands
from discord.ext.commands import Bot, BucketType, Context, Cooldown, clean_content

from config import CONFIG
from utils.utils import get_name_and_content

LONG_HELP_TEXT = """
Apollo is smarter than you think...

GPT will be given the full chain of replied messages, *it does not look at latest messages*.
If you want to set a custom initial prompt, use `!prompt <prompt>` then reply to that.
"""

SHORT_HELP_TEXT = "Apollo is smarter than you think..."

mentions = AllowedMentions(everyone=False, users=False, roles=False, replied_user=True)
chat_cmd = CONFIG.PREFIX + "chat "
prompt_cmd = CONFIG.PREFIX + "prompt "


class ChatGPT(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        openai.api_key = CONFIG.OPENAI_API_KEY
        self.model = "gpt-3.5-turbo"
        self.system_prompt = CONFIG.AI_SYSTEM_PROMPT
        if CONFIG.AI_INCLUDE_NAMES:
            self.system_prompt += "\nYou are in a Discord chat room, each message is prepended by the name of the message's author separated by a colon. Omit your name when responding to messages."
        self.cooldowns = {}

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def prompt(self, ctx: Context, *, message: str):
        # Effectively a dummy command, since just needs something to allow a prompt message
        await ctx.message.add_reaction("✅")

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def chat(self, ctx: Context, *, message: str):
        await self.cmd(ctx)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Avoid replying to bot or msg that triggers the command anyway
        if message.author.bot or message.content.startswith(CONFIG.PREFIX):
            return

        # Only engage if replying to Apollo, use !chat to trigger otherwise
        previous = await self.fetch_previous(message)
        if not previous:
            return
        if not previous.author.id == self.bot.user.id:
            # Allow if replying to prompt
            if not previous.content.startswith(prompt_cmd):
                return

        ctx = await self.bot.get_context(message)
        await self.cmd(ctx)

    async def cmd(self, ctx: Context):
        # Create history chain
        messages = await self.create_history(ctx.message)
        if not messages or await self.in_cooldown(ctx):
            return

        # If valid, dispatch to OpenAI and reply
        async with ctx.typing():
            response = await self.dispatch_api(messages)
            if response:
                await ctx.reply(response, allowed_mentions=mentions)

    async def create_history(self, message):
        message_chain = await self.get_message_chain(message)

        # If a message in the chain triggered a !chat or !prompt or /chat
        is_cmd = (
            lambda m: m.content.startswith(chat_cmd)
            or m.content.startswith(prompt_cmd)
            or (m.interaction is not None and m.interaction.name == "chat")
        )
        if not any(map(is_cmd, message_chain)):
            return

        # If first message starts with !prompt use that for initial
        initial_msg = message_chain[0].content
        if initial_msg.startswith(prompt_cmd):
            initial = initial_msg.removeprefix(prompt_cmd)
            message_chain = message_chain[1:]
        else:
            initial = self.system_prompt
        messages = [dict(role="system", content=initial)]

        # Convert to dict form for request
        for msg in message_chain:
            role = "assistant" if msg.author == self.bot.user else "user"
            content = msg.clean_content.removeprefix(chat_cmd)
            if CONFIG.AI_INCLUDE_NAMES and msg.author != self.bot.user:
                name, content = get_name_and_content(msg)
                content = f"{name}: {content.removeprefix(chat_cmd)}"
            messages.append(dict(role=role, content=content))
        return messages

    async def in_cooldown(self, ctx):
        # If is in allowed channel
        if ctx.channel.id in CONFIG.AI_CHAT_CHANNELS:
            return False
        if isinstance(ctx.channel, discord.Thread):
            if ctx.channel.parent.id in CONFIG.AI_CHAT_CHANNELS:
                return False
        if isinstance(ctx.channel, discord.DMChannel):
            return False

        # Limit with 60s cooldown
        now = datetime.now(timezone.utc)
        if self.cooldowns.get(ctx.channel.id):
            cutoff = now - timedelta(seconds=60)
            if ctx.message.created_at > cutoff:
                await ctx.message.add_reaction("⏱️")
                return True
        self.cooldowns[ctx.channel.id] = now
        return False

    async def dispatch_api(self, messages) -> Optional[str]:
        logging.info(f"Making OpenAI request: {messages}")

        # Make request
        response = await openai.ChatCompletion.acreate(
            model=self.model, messages=messages
        )
        logging.info(f"OpenAI Response: {response}")

        # Remove prefix that chatgpt might add
        reply = response.choices[0].message.content
        if CONFIG.AI_INCLUDE_NAMES:
            reply = reply.removeprefix("Apollo: ")
            reply = reply.removeprefix("apollo: ")
            reply = reply.removeprefix(f"{self.bot.user.display_name}: ")

        # Truncate if long
        if len(reply) > 3990:
            reply = reply[:3990] + "..."
        return reply

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
