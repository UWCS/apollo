import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import aiohttp
import discord
import openai
from discord import AllowedMentions
from discord.ext import commands, tasks
from discord.ext.commands import (
    Bot,
    BucketType,
    Context,
    Cooldown,
    check,
    clean_content,
)

from cogs.commands.openaiadmin import is_author_banned_openai, is_user_banned_openai
from config import CONFIG
from utils.utils import get_name_and_content, split_into_messages

LONG_HELP_TEXT = """
Apollo is smarter than you think...

GPT will be given the full chain of replied messages, *it does not look at latest messages*.
If you want to set a custom initial prompt, use `!prompt <prompt>` then reply to that.
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
        # When apollo gained ai capabilities, for calculating API costs
        self.ai_epoch = date(year=2023, month=3, day=1)
        self.usage_endpoint = "https://api.openai.com/dashboard/billing/usage"

        openai.api_key = CONFIG.OPENAI_API_KEY
        self.model = "gpt-4"
        self.system_prompt = CONFIG.AI_SYSTEM_PROMPT
        if CONFIG.AI_INCLUDE_NAMES:
            self.system_prompt += "\nYou are in a Discord chat room, each message is prepended by the name of the message's author separated by a colon. Omit your name when responding to messages."
        self.cooldowns = {}

        # have to start the task loop
        self.update_channel_descriptions.start()

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def prompt(self, ctx: Context, *, message: str):
        # Effectively a dummy command, since just needs something to allow a prompt message
        if await self.in_cooldown(ctx):
            return
        await ctx.message.add_reaction("✅")

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    @check(is_author_banned_openai)
    async def chat(self, ctx: Context, *, message: Optional[str] = None):
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
        if is_user_banned_openai(ctx.author.id):  # if user is banned error
            return await ctx.message.reply(
                "You are banned from using openAI commands, please contact an exec if you think this is a mistake"
            )

        # Create history chain
        messages = await self.create_history(ctx.message)
        if not messages or await self.in_cooldown(ctx):
            return

        # If valid, dispatch to OpenAI and reply
        async with ctx.typing():
            response = await self.dispatch_api(messages)
            if response:
                prev = ctx.message
                for content in split_into_messages(response):
                    prev = await prev.reply(content, allowed_mentions=mentions)

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
            initial = clean(initial_msg, prompt_cmd)
            message_chain = message_chain[1:]
        else:
            initial = self.system_prompt
        messages = [dict(role="system", content=initial)]

        # Convert to dict form for request
        for msg in message_chain:
            role = "assistant" if msg.author == self.bot.user else "user"
            # Skip empty messages (if you want to invoke on a pre-existing chain)
            if not (content := clean(msg.clean_content, chat_cmd)):
                continue
            # Add name to start of message for user msgs
            if CONFIG.AI_INCLUDE_NAMES and msg.author != self.bot.user:
                name, content = get_name_and_content(msg)
                content = f"{name}: {clean(content, chat_cmd)}"

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
            name = f"{self.bot.user.display_name}: "
            reply = clean(reply, "Apollo: ", "apollo: ", name)

        return reply

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

    @tasks.loop(minutes=30)
    async def update_channel_descriptions(self):
        """
        Update the AI chat description to include the current API usage.
        Assumes the channel to be updated is the first one in the list.
        Runs in a task loop, firing periodically
        """
        channel = self.bot.get_channel(CONFIG.AI_CHAT_CHANNELS[0])
        if not isinstance(channel, discord.TextChannel):
            raise Exception("First channel in AI_CHAT_CHANNELS must be a text channel")
        spent_usd = await self.get_api_usage() / 100

        # we need to do currency conversion
        async with aiohttp.ClientSession() as session:
            resp = await session.get(
                "https://api.exchangerate.host/convert?from=USD&to=GBP"
            )
            rate = (await resp.json())["result"]

        spent_gbp = round(spent_usd * rate, 4)
        await channel.edit(
            topic=f"Chat with Apollo here! API usage to date: £{spent_gbp}"
        )

    @update_channel_descriptions.before_loop
    async def before_updates(self):
        """
        Tells the task loop to wait until the bot is ready before starting
        """
        await self.bot.wait_until_ready()

    async def get_api_usage(self) -> float:
        """
        Gets the cumulative usage of the OpenAI API since self.ai_epoch
        Returns the usage in USD cents
        **The API endpoint being used is undocumented, and may break at any time**
        """
        # we have to fetch it in 100 day chunks, because of odd API limitations
        chunks = [date.today() + timedelta(days=1)]
        while chunks[-1] > self.ai_epoch:
            chunks.append(chunks[-1] - timedelta(days=98))

        date_pairs = (
            {"start_date": str(start), "end_date": str(end)}
            for (end, start) in zip(chunks, chunks[1:])
        )

        headers = {"Authorization": f"Bearer {CONFIG.OPENAI_API_KEY}"}
        async with aiohttp.ClientSession(headers=headers) as session:
            # asyncio.gather schedules all the futures simultaneously
            responses = await asyncio.gather(
                *(session.get(url=self.usage_endpoint, params=ps) for ps in date_pairs)
            )

            if all(r.ok for r in responses):
                # happy path
                # fetching response content as json is a coro
                usage = await asyncio.gather(*(r.json() for r in responses))
                return sum(float(u["total_usage"]) for u in usage)
            else:
                # pin down the errors
                statuses = ", ".join(
                    f"{r.status}: {r.reason}" for r in responses if r.status != 200
                )
                raise Exception(
                    "Failed to fetch OpenAI API usage: error responses were: "
                    + statuses
                )


async def setup(bot: Bot):
    await bot.add_cog(ChatGPT(bot))
