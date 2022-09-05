import io

import discord
import requests
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content
from discord.file import File

from utils.clean import CleanContent

LONG_HELP_TEXT = """
Render a LaTeX maths expression to an image and show it in-line.
"""

SHORT_HELP_TEXT = """Display LaTeX formatted maths."""

API_URL = "https://latex.codecogs.com/png.image?\dpi{300}"

class Tex(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    # @app_commands.command(name="tex", description=SHORT_HELP_TEXT)
    # async def tex_slash(self, interaction: discord.Interaction, text: str):
    #     await interaction.response.defer()
    #     result = await self.tex_base(text)
    #     print(result)
    #     await interaction.followup.send(**result)

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def tex(self, ctx: Context, *, message: str):
        message = await clean_content().convert(ctx, message)

        # Input filtering
        if not message:
            await ctx.send("Your message contained nothing to render")

        if message[0] == "```tex":
            message = ("```", *message[1:])

        tex_code = message.strip('`$')
        url = API_URL + requests.utils.quote(tex_code)
        r = requests.get(url)
        c = io.BytesIO(r.content)

        # Load the image as a file to be attached to an image
        img_file = File(c, filename="tex.png")
        await ctx.send(f"Here you go! :abacus:", file=img_file)


async def setup(bot: Bot):
    await bot.add_cog(Tex(bot))
