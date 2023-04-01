import logging
import discord
import openai
from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content
import aiohttp
import asyncio
from io import BytesIO

from config import CONFIG

LONG_HELP_TEXT = """
Apollo is more creative than you think...

Apollo can now generate imagefes using openAI's DALL-E model. 
To use Apollo, simply type `!dalle <prompt>` . Apollo will then generate an image based on the prompt.
"""

SHORT_HELP_TEXT = "Apollo is more creative than you think..."

chat_cmd = CONFIG.PREFIX + "dalle"

def clean(msg, *prefixes):
    for pre in prefixes:
        msg = msg.strip().removeprefix(pre)
    return msg.strip()


class Dalle(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        openai.api_key = CONFIG.OPENAI_API_KEY
        self.cooldowns = {}

    @commands.command()
    async def dalle(self, ctx: Context, *, prompt: clean_content):
        prompt = clean(prompt, chat_cmd, CONFIG.PREFIX)
        url = self.generate_image(prompt)
        image = self.get_image(url)
        if image is not None:
           await ctx.reply(file=image, mention_author=True)
        else:
            await ctx.reply("Failed to generate image", mention_author=True)
        

    async def generate_image(self, prompt): # generates the image from open ai
        logging.info(f"Generating image with prompt: {prompt}")
        response = await openai.Image.acreate(
            prompt=prompt,
            n=1,
            size="256x256",
        )
        return response["data"][0]["url"] # returns the url of the image
    
    async def get_image(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    logging.info("successfully got image")
                    return discord.File(BytesIO(await response.read()), filename="image.png")
                else:
                    logging.info("failed to get image")
                    return None

async def setup(bot: Bot):
    await bot.add_cog(Dalle(bot))