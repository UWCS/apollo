import logging
import discord
import openai
from discord import AllowedMentions
from discord.ext import commands
from discord.ext.commands import Bot, BucketType, Context, Cooldown, clean_content
import requests
from io import BytesIO

from config import CONFIG
from utils.utils import get_name_and_content

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
        

    def generate_image(self, prompt): # generates the image from open ai
        logging.info(f"Generating image with prompt: {prompt}")
        respone = openai.Image.create(
            prompt=prompt,
            n=1,
            size="256x256",
        )
        return respone["data"][0]["url"] # returns the url of the image
    
    def get_image(self, url):
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            logging.info("successfully got image")
            return discord.File(BytesIO(response.content), filename="image.png")
        else:
            logging.info("failed to get image")
            return None

async def setup(bot: Bot):
    await bot.add_cog(Dalle(bot))
