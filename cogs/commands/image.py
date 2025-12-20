import logging
from enum import Enum
from io import BytesIO

import discord
from discord.ext import commands
from discord.ext.commands import Bot, Context, check, clean_content
from openai import AsyncOpenAI

from cogs.commands.openaiadmin import is_author_banned_openai
from config import CONFIG
from utils import get_file_from_url

LONG_HELP_TEXT = """
Apollo is more creative than you think...

Apollo can now generate images using openAI's image generation model.
To use, simply type `!image <prompt>` or `/image <prompt>`. Apollo will then generate an image based on the prompt.
"""

SHORT_HELP_TEXT = "Apollo is more creative than you think..."


IMAGE_RESOLUTION = "1024x1024"
MODEL = "gpt-image-1.5"


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


class Image(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.openai_client = AsyncOpenAI(api_key=CONFIG.OPENAI_API_KEY)

    @commands.dynamic_cooldown(get_cooldown, type=commands.BucketType.channel)
    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    @check(is_author_banned_openai)
    async def image(self, ctx: Context, *, prompt: str):
        """Generates an image based on the prompt using DALL-E"""

        prompt = await clean_content().convert(ctx, prompt)

        # if no prompt error (i think unused thanks to previous error handling but nice to have)
        if prompt == "":
            await ctx.reply("Please provide a prompt", mention_author=True)
            return

        async with ctx.typing():  # show typing whilst generating image
            image = await self.generate_image(prompt, [])
        if image is None:  # if image is not created error
            return await ctx.reply(
                "Failed to generate image :wah:", mention_author=True
            )
        view = ImageView(timeout=None, bot=self.bot)  # otherwise reply with image
        await ctx.reply(prompt, file=image, mention_author=True, view=view)

    async def generate_image(self, prompt: str, previous_images: list[bytes]):
        """gets image from openAI and returns that image"""
        logging.info(f"Generating image with prompt: {prompt}")

        def bytes_to_file(file_bytes: bytes):
            f = BytesIO(file_bytes)
            f.name = "image.png"
            return f

        response = (
            await self.openai_client.images.generate(
                model=MODEL, prompt=prompt, size=IMAGE_RESOLUTION
            )
            if previous_images == []
            else await self.openai_client.images.edit(
                model=MODEL,
                prompt=prompt,
                image=list(map(bytes_to_file, previous_images)),
                size=IMAGE_RESOLUTION,
            )
        )
        logging.info(f"OpenAI Image Response: {response}")
        return await get_file_from_url(response.data[0].url)


class Mode(Enum):  # enums for the different modess
    REGENERATING = "Regenerating"
    VARIANT = "Creating variant"


class ImageView(discord.ui.View):
    def __init__(self, timeout: float | None, bot: Bot) -> None:
        super().__init__(timeout=timeout)
        self.image_cog = bot.get_cog("Image")  # get image cog to use image generation

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

        if not await is_author_banned_openai(interaction):
            return

        self.edit_buttons(True)  # disables buttons
        await interaction.response.edit_message(
            content=f"{mode.value} ⌛", view=self
        )  # send initial confirmation (discord needs response within 30s)

        # get image
        message = interaction.message
        previous_images = []
        for attachment in message.attachments:
            previous_images.append(await attachment.read())
        new_image = await self.image_cog.generate_image(
            prompt=message.content,
            previous_images=previous_images if mode == Mode.VARIANT else [],
        )
        if new_image is None:
            await interaction.followup.edit_message(
                message.id,
                content="Failed to generate image :wah:",
                view=self,
            )
            self.edit_buttons(False)  # re-enables buttons
            return

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
                file=new_image,
                view=self,
            )
        else:
            # otherwise we can just edit the message
            await message.add_files(new_image)
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
    await bot.add_cog(Image(bot))
