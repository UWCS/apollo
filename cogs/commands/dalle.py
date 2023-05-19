import logging
from enum import Enum

import discord
import openai
from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content
from openaiadmin import OpenAIAdmin

import utils
from config import CONFIG

LONG_HELP_TEXT = """
Apollo is more creative than you think...

Apollo can now generate images using openAI's DALL-E model.
To use, simply type `!dalle <prompt>` or `/dalle <prompt>`. Apollo will then generate an image based on the prompt.
Once generated buttons can be used to regenerate the image (create a new image based on the prompt) or create a variant of the the most recent image.
"""

SHORT_HELP_TEXT = "Apollo is more creative than you think..."


IMAGE_RESOLUTION = "256x256"  # resolution of images (maybe change later?) (you're welcome treasurer btw)


def get_cooldown(ctx: Context):
    """cooldown for command: 1s in ai channels (or DMs), 60s everywhere else"""
    if ctx.channel.id in CONFIG.AI_CHAT_CHANNELS:
        return commands.Cooldown(1, 1)
    if isinstance(ctx.channel, discord.Thread) and ctx.channel.parent:
        if ctx.channel.parent.id in CONFIG.AI_CHAT_CHANNELS:
            return commands.Cooldown(1, 1)
    if isinstance(ctx.channel, discord.DMChannel):
        return commands.Cooldown(1, 1)
    return commands.Cooldown(1, 60)


class Dalle(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        openai.api_key = CONFIG.OPENAI_API_KEY

    @commands.dynamic_cooldown(get_cooldown, type=commands.BucketType.channel)
    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def dalle(self, ctx: Context, *, prompt: str):
        """Generates an image based on the prompt using DALL-E"""

        if await OpenAIAdmin.is_user_banned(ctx.author):  # if user is banned error
            return await ctx.reply(
                "You are banned from using openAI commands, please contact an exec if you think this is a mistake"
            )

        prompt = await clean_content().convert(ctx, prompt)

        # if no prompt error (i think unused thanks to previous error handling but nice to have)
        if prompt == "":
            await ctx.reply("Please provide a prompt", mention_author=True)
            return

        async with ctx.typing():  # show typing whilst generating image
            url = await self.generate_image(prompt)
            image = await utils.get_file_from_url(url)
        if image is None:  # if image is not created error
            return await ctx.reply(
                "Failed to generate image :wah:", mention_author=True
            )
        view = DalleView(timeout=None, bot=self.bot)  # otherwise reply with image
        await ctx.reply(prompt, file=image, mention_author=True, view=view)

    async def generate_image(self, prompt: str):
        """gets image from openAI and returns url for that image"""
        logging.info(f"Generating image with prompt: {prompt}")
        response = await openai.Image.acreate(
            prompt=prompt,
            n=1,
            size=IMAGE_RESOLUTION,  # maybe change later? (you're welcome treasurer btw)
        )
        return response["data"][0]["url"]

    @staticmethod
    async def generate_variant(image: bytes):
        """generates a variant of the image"""
        response = await openai.Image.acreate_variation(
            image=image,
            n=1,
            size=IMAGE_RESOLUTION,
        )
        return response["data"][0]["url"]


class Mode(Enum):  # enums for the different modess
    REGENERATING = "Regenerating"
    VARIANT = "Creating variant"


class DalleView(discord.ui.View):
    def __init__(self, timeout: float | None, bot: Bot) -> None:
        super().__init__(timeout=timeout)
        self.dalle_cog = bot.get_cog("Dalle")  # get dalle cog to use image generation

    @discord.ui.button(label="Regenerate", style=discord.ButtonStyle.primary)
    async def regenerate(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """renegerates the image"""
        await self.new_image(interaction, Mode.REGENERATING)

    @discord.ui.button(label="Variant", style=discord.ButtonStyle.primary)
    async def variant(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """generates a variant of the image"""
        await self.new_image(interaction, Mode.VARIANT)

    async def new_image(self, interaction: discord.Interaction, mode: Mode):
        """generic function for updating the image"""

        if await OpenAIAdmin.is_user_banned(ctx.author):  # if user is banned error
            return await ctx.reply(
                "You are banned from using openAI commands, please contact an exec if you think this is a mistake"
            )

        self.edit_buttons(True)  # disables buttons
        await interaction.response.edit_message(
            content=f"{mode.value} ⌛", view=self
        )  # send initial confirmation (discord needs response within 30s)
        message = interaction.message  # gets message for use later
        new_url = ""
        if mode == Mode.REGENERATING:  # generates new image
            new_url = await self.dalle_cog.generate_image(message.content)
        elif mode == Mode.VARIANT:  # creates variant of image
            new_url = await self.dalle_cog.generate_variant(
                await utils.get_from_url(message.attachments[-1].url)
            )
        new_file = await utils.get_file_from_url(new_url)  # makes the new file
        self.edit_buttons(False)  # re-enables buttons
        if len(message.attachments) == 10:
            # discord only allows 10 attachments per message so we need to send a new message
            items = self.children
            self.clear_items()  # removes all children and saves for later
            await interaction.followup.edit_message(
                message.id, content=message.content, view=self
            )
            for item in items:  # re-adds all children
                self.add_item(item)
            await interaction.followup.send(
                message.content,
                file=new_file,
                view=self,
            )
        else:
            # otherwise we can just edit the message
            await message.add_files(new_file)
            self.edit_buttons(False)  # for some reason need to re-enable buttons again
            await interaction.followup.edit_message(
                message.id, content=message.content, view=self
            )

    async def on_timeout(self) -> None:
        await self.message.reply("timeout")
        self.edit_buttons(True)

    def edit_buttons(self, state: bool):
        for button in self.children:
            button.disabled = state


async def setup(bot: Bot):
    await bot.add_cog(Dalle(bot))
