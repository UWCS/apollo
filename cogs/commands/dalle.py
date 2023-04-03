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
To use, simply type `!dalle <prompt>` or `/dalle <prompt>`. Apollo will then generate an image based on the prompt.
Once generated buttons can be used to regenerate the image (create a new image based on the prompt) or create a variant of the original image.
"""

SHORT_HELP_TEXT = "Apollo is more creative than you think..."


class Dalle(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        openai.api_key = CONFIG.OPENAI_API_KEY

    #def get_cooldown(ctx):
        #"""cooldown for command: 1s in ai channels (or DMs), 60s everywhere else"""
        #if ctx.channel.id in CONFIG.AI_CHAT_CHANNELS:
            #return commands.cooldown(1, 1)
        #if isinstance(ctx.channel, discord.Thread) and ctx.channel.parent:
            #if ctx.channel.parent.id in CONFIG.AI_CHAT_CHANNELS:
                #return commands.cooldown(1, 1)
        #if isinstance(ctx.channel, discord.DMChannel):
            #return commands.cooldown(1, 1)
        #return commands.cooldown(1, 60)

    #@commands.dynamic_cooldown(get_cooldown, commands.BucketType.channel)
    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def dalle(self, ctx: Context, *, args: str):
        """Generates an image based on the prompt using DALL-E"""
        prompt = await clean_content().convert(ctx, args)

        if prompt == "":  # if no prompt error
            await ctx.reply("Please provide a prompt", mention_author=True)
            return

        async with ctx.typing():  # show typing whilst generating image
            url = await self.generate_image(prompt)
            image = discord.File(
                await self.get_image(url),
                filename="image.png"
            )
        if image is not None:
            view = DalleView(timeout=None)
            message = await ctx.reply(prompt, file=image, mention_author=True, view=view)
            view.message = message
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
                    return BytesIO(await response.read())
                else:
                    logging.info("failed to get image")
                    return None

    async def generate_variant(self, image):
        """generates a variant of the image"""
        byte_array = image.getvalue()
        response = await openai.Image.acreate_variation(
            image=byte_array,
            n=1,
            size="256x256",
        )
        return response["data"][0]["url"]


class DalleView(discord.ui.View):
    @discord.ui.button(label="Regenerate", style=discord.ButtonStyle.primary)
    async def regenerate(self, interaction, button):
        """renegerates the image"""
        self.edit_buttons(True)  # disables buttons
        message = interaction.message  # gets message for use later
        logging.info(f"regenerating image with prompt: {message.content}")
        await interaction.response.edit_message(
            content="Regenerating...", attachments=[], view=self
        )  # send initial confirmatino (dsicord needs response within 30s)
        new_url = await Dalle.generate_image(message.content)  # generates new image
        new_image = discord.File(await Dalle.get_image(new_url), filename="image.png")
        self.edit_buttons(False)  # re-enables buttons
        await interaction.followup.edit_message(
            message.id, content=message.content, attachments=[new_image], view=self
        )

    @discord.ui.button(label="Variant", style=discord.ButtonStyle.primary)
    async def variant(self, interaction, button):
        """generates a variant of the image"""
        logging.info("generating variant")
        self.edit_buttons(True)
        message = interaction.message
        await interaction.response.edit_message(
            content="Creating variant...", attachments=[], view=self
        )
        new_url = await Dalle.generate_variant(
            await Dalle.get_image(message.attachments[0].url)
        )
        new_image = discord.File(await Dalle.get_image(new_url), filename="image.png")
        self.edit_buttons(False)
        await interaction.followup.edit_message(
            message.id, content=message.content, attachments=[new_image], view=self
        )

    async def on_timeout(self) -> None:
        await self.message.reply("timeout")
        await self.edit_buttons(True)

    def edit_buttons(self, state):
        for button in self.children:
            button.disabled = state


async def setup(bot: Bot):
    await bot.add_cog(Dalle(bot))
