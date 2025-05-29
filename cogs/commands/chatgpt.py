import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
import openai
from discord import AllowedMentions
from discord.ext import commands
from discord.ext.commands import (
    Bot,
    Context,
)

from cogs.commands.openaiadmin import is_author_banned_openai
from config import CONFIG
from utils.utils import get_name_and_content, split_into_messages

LONG_HELP_TEXT = """
Apollo is smarter than you think...

GPT will be given the full chain of replied messages, *it does not look at latest messages*.
If you want to set a custom initial prompt, use `!prompt <prompt>` then reply to that.
This defaults to gpt4.1 mini, if you need gpt4.1 full, use `--full` to switch (will inherit down conversation)
"""

SHORT_HELP_TEXT = "Apollo is smarter than you think..."

mentions = AllowedMentions(everyone=False, users=False, roles=False, replied_user=True)
chat_cmd = CONFIG.PREFIX + "chat"
prompt_cmd = CONFIG.PREFIX + "prompt"


def clean(msg, *prefixes):
    for pre in prefixes:
        msg = msg.strip().removeprefix(pre)
    return msg.strip()


class ChatGPT(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        openai.api_key = CONFIG.OPENAI_API_KEY
        self.system_prompt = CONFIG.AI_SYSTEM_PROMPT
        if CONFIG.AI_INCLUDE_NAMES:
            self.system_prompt += "\nYou are in a Discord chat room, each message is prepended by the name of the message's author separated by a colon."
        self.cooldowns = {}

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def prompt(self, ctx: Context, *, message: str):
        # Effectively a dummy command, since just needs something to allow a prompt message
        if await self.in_cooldown(ctx):
            return
        await ctx.message.add_reaction("✅")

    @commands.hybrid_command(
        help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT, usage="[--full] <message ...>"
    )
    async def chat(self, ctx: Context, *, message: str):
        await self.cmd(ctx, message)

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
        await self.cmd(ctx, message)

    async def cmd(self, ctx: Context, message: str):
        if not await is_author_banned_openai(ctx):
            return

        # Create history chain
        messages, full = await self.create_history(message, ctx)
        if not messages or await self.in_cooldown(ctx):
            return

        # If valid, dispatch to OpenAI and reply
        async with ctx.typing():
            response = await self.dispatch_api(messages, full)
            if response:
                prev = ctx
                for content in split_into_messages(response):
                    prev = await prev.reply(content, allowed_mentions=mentions)

    async def create_history(self, message, ctx):
        # if message is string then slash command
        message_chain = await self.get_message_chain(message, ctx)
        full = False

        # If a message in the chain triggered a !chat or !prompt or /chat
        def is_cmd(m):
            if isinstance(m, str):
                return True
            return (
                m.content.startswith(chat_cmd)
                or m.content.startswith(prompt_cmd)
                or m.interaction is not None
                and m.interaction.name == "chat"
            )

        if not any(map(is_cmd, message_chain)):
            return

        # If first message starts with !prompt use that for initial
        initial_msg = (
            message_chain[0]
            if isinstance(message_chain[0], str)
            else message_chain[0].content
        )
        if initial_msg.startswith(prompt_cmd):
            initial = clean(initial_msg, prompt_cmd)
            if initial.startswith("--full"):
                full = True
                initial = clean(initial, "--full")
            message_chain = message_chain[1:]
        else:
            initial = self.system_prompt
        messages = [dict(role="system", content=initial)]

        # Convert to dict form for request
        for msg in message_chain:
            role = (
                "user"
                if isinstance(msg, str)  # slash commands will always be users
                else "assistant" if msg.author == self.bot.user else "user"
            )
            content = msg if isinstance(msg, str) else msg.clean_content
            # Skip empty messages (if you want to invoke on a pre-existing chain)
            if not (content := clean(content, chat_cmd)):
                continue
            if content.startswith("--full"):
                full = True
                content = clean(content, "--full")

            if re.match(
                r"https://cdn.discordapp.com/attachments/\d+/\d+/\w+\.\w+", content
            ):
                messages.append(
                    dict(
                        role=role,
                        content=[
                            {
                                "type": "image_url",
                                "image_url": {"url": content, "detail": "low"},
                            }
                        ],
                    )
                )
            else:
                # Add name to start of message for user msgs
                if CONFIG.AI_INCLUDE_NAMES and (
                    isinstance(msg, str) or msg.author != self.bot.user
                ):
                    name, content = (
                        get_name_and_content(msg)
                        if not isinstance(msg, str)
                        else (ctx.author.display_name, content)
                    )
                    content = f"{name}: {clean(content, chat_cmd, '--full')}"
                messages.append(
                    dict(role=role, content=[{"type": "text", "text": content}])
                )

        return messages, full

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

    async def dispatch_api(self, messages, full) -> Optional[str]:

        # Make request
        logging.info(f"Making OpenAI request: {messages}")
        model = "gpt-4.1" if full else "gpt-4.1-mini"
        response = await openai.ChatCompletion.acreate(model=model, messages=messages)
        logging.info(f"OpenAI Response: {response}")

        # Remove prefix that chatgpt might add
        reply = response.choices[0].message.content
        if CONFIG.AI_INCLUDE_NAMES:
            name = f"{self.bot.user.display_name}: "
            reply = clean(reply, "Apollo: ", "apollo: ", name)

        return reply

    async def get_message_chain(
        self, message: discord.Message | str, ctx: Context
    ) -> list[discord.Message | str]:
        """
        Traverses a chain of replies to get a thread of chat messages between a user and Apollo.
        """
        if message is None:
            return []
        previous = (
            await self.fetch_previous(message)
            if isinstance(message, discord.Message)
            else None
        )
        append = [message]

        attachments = (
            message.attachments
            if isinstance(message, discord.Message)
            else ctx.message.attachments
        )
        for attachment in attachments:
            if attachment.content_type.startswith("image"):
                append.append(attachment.url)
        return (await self.get_message_chain(previous, ctx)) + append

    async def fetch_previous(
        self, message: discord.Message
    ) -> Optional[discord.Message]:
        if message.reference is not None and message.reference.message_id is not None:
            return await message.channel.fetch_message(message.reference.message_id)
        return None


async def setup(bot: Bot):
    await bot.add_cog(ChatGPT(bot))
