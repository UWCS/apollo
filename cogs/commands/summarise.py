import logging
from typing import Optional

import openai
from discord import AllowedMentions
from discord.ext import commands
from discord.ext.commands import Bot, Context

from cogs.commands.openaiadmin import is_author_banned_openai
from config import CONFIG
from math import exp, ceil
from utils.utils import split_into_messages

LONG_HELP_TEXT = """
Too much yapping? Summarise what people have said using the power of the GPT overlords!
"""

SHORT_HELP_TEXT = """Summarise messages."""

mentions = AllowedMentions(everyone=False, users=False, roles=False, replied_user=True)
model = "gpt-4o-mini"

# weights/coefficients for sigmoid function
a = 750
b = 7
c = 400


def clean(msg, *prefixes):
    for pre in prefixes:
        msg = msg.strip().removeprefix(pre)
    return msg.strip()


class Summarise(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        openai.api_key = CONFIG.OPENAI_API_KEY




    

    @commands.cooldown(CONFIG.SUMMARISE_LIMIT, CONFIG.SUMMARISE_COOLDOWN * 60, commands.BucketType.channel)
    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def tldr(
        self, ctx: Context, number_of_messages: int = 100, bullet_point_output: bool = False ):
        

        number_of_messages = CONFIG.SUMMARISE_MESSAGE_LIMIT if number_of_messages > CONFIG.SUMMARISE_MESSAGE_LIMIT else number_of_messages
        
        # avoid banned users
        if not await is_author_banned_openai(ctx):
            await ctx.send("You are banned from OpenAI!")
            return

        # get the last "number_of_messages" messages from the current channel and build the prompt
        prompt = self.build_prompt(bullet_point_output, ctx.channel, self.sigmoid(number_of_messages))

        messages = ctx.channel.history(limit=number_of_messages)
        messages = await self.create_message(messages, prompt, ctx)

        # send the prompt to the ai overlords to process
        async with ctx.typing():
            response = await self.dispatch_api(messages)
            if response:
                prev = ctx.message
                for content in split_into_messages(response):
                    prev = await prev.reply(content, allowed_mentions=mentions)

    async def dispatch_api(self, messages) -> Optional[str]:
        logging.info(f"Making OpenAI request: {messages}")

        # Make request
        response = await openai.ChatCompletion.acreate(model=model, messages=messages)
        logging.info(f"OpenAI Response: {response}")

        # Remove prefix that chatgpt might add
        reply = response.choices[0].message.content
        if CONFIG.AI_INCLUDE_NAMES:
            name = f"{self.bot.user.display_name}: "
            reply = clean(reply, "Apollo: ", "apollo: ", name)
        return reply

    async def create_message(self, message_chain, prompt, ctx):
        # get initial prompt
        initial = prompt + "\n"

        # for each message, append it to the prompt as follows --- author : message \n
        message_length = 0
        async for msg in message_chain:
            if CONFIG.AI_INCLUDE_NAMES and msg.author != self.bot.user:
                message_length += len(msg.content.split())
                initial += msg.author.name + ": " + msg.content + "\n"
        messages = [dict(role="system", content=initial)]

        return messages


    def build_prompt(self, bullet_points, channel_name, response_size):

        bullet_points = "Put it in bullet points for readability." if bullet_points else ""
        prompt = f"""People yap too much, I don't want to read all of it. The topic is related to {channel_name}. In {response_size} words or less give me the gist of what is being said. {bullet_points} Note that the messages are in reverse chronological order:
        """
        return prompt

    def sigmoid(self, x):
        return int(ceil(c / (1 + b * exp((-x)/ a))))

async def setup(bot: Bot):
    await bot.add_cog(Summarise(bot))
