import logging
from io import BytesIO

import aiohttp
import discord
import openai
from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content

from config import CONFIG

LONG_HELP_TEXT = """
Apollo is more creative than you think...

Apollo can now generate images using openAI's DALL-E model. 
To use, simply type `!dalle <prompt>` . Apollo will then generate an image based on the prompt.
"""

SHORT_HELP_TEXT = "Apollo is more creative than you think..."


class Dalle(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        openai.api_key = CONFIG.OPENAI_API_KEY
        self.cooldowns = {}

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def dalle(self, ctx: Context, *, args: str):
        """Generates an image based on the prompt using DALL-E"""
        prompt = await clean_content().convert(ctx, args)

        if prompt == "":
            await ctx.reply("Please provide a prompt", mention_author=True)
            return

        async with ctx.typing():
            url = await self.generate_image(prompt)
            image = await self.get_image(url)
        if image is not None:
            await ctx.reply(file=image, mention_author=True)
        else:
            await ctx.reply("Failed to generate image :wah:", mention_author=True)

    async def generate_image(self, prompt):
        """gets image from openAI and returns url for that image"""
        logging.info(f"Generating image with prompt: {prompt}")
        response = await openai.Image.acreate(
            prompt=prompt,
            n=1,
            size="256x256",  # maybe change later? (you're wlecome treasurer btw)
        )
        return response["data"][0]["url"]

    async def get_image(self, url):
        """gets image from url and returns it as a discord file"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    logging.info("successfully got image")
                    return discord.File(
                        BytesIO(await response.read()), filename="image.png"
                    )
                else:
                    logging.info("failed to get image")
                    return None


async def setup(bot: Bot):
    await bot.add_cog(Dalle(bot))
