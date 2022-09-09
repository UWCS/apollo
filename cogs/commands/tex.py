import io

import requests
from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content
from discord.file import File
from PIL import Image

LONG_HELP_TEXT = """
Render a LaTeX maths expression to an image and show it in-line.
"""

SHORT_HELP_TEXT = """Display LaTeX formatted maths."""

API_URL = r"https://latex.codecogs.com/png.image?\dpi{300}\bg{black}"


class Tex(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def tex(self, ctx: Context, *, tex: str):
        tex_raw = await clean_content().convert(ctx, tex)

        # Input filtering
        if not tex_raw:
            await ctx.send("Your message contained nothing to render")

        if tex_raw[0] == "```tex":
            tex_raw = ("```", *tex_raw[1:])

        tex_code = tex_raw.strip("`")
        # If $ are included, wrap in \text to format normal text
        if tex_code.count("$") >= 2:
            tex_code = f"\\text{{{tex_code}}}"

        # Make request
        url = API_URL + requests.utils.quote(tex_code)
        r = requests.get(url)
        c = io.BytesIO(r.content)

        # Mask in colours (API only does a few colours)
        mask = Image.open(c).convert("L")
        white = Image.new("RGB", (mask.width, mask.height), (255, 255, 255))
        bg = Image.new("RGB", (mask.width, mask.height), (54, 57, 63))
        result = Image.composite(white, bg, mask)
        result.save("res.png")

        # Save masked image
        img = io.BytesIO()
        result.save(img, format="png")
        img.seek(0)

        # Load the image as a file to be attached to an image
        img_file = File(img, filename="tex.png")
        if r.status_code == 200:
            await ctx.send(f"Here you go! :abacus:", file=img_file)
        else:
            await ctx.message.add_reaction("❓")
            if ctx.interaction:
                await ctx.send("Invalid Equation")


async def setup(bot: Bot):
    await bot.add_cog(Tex(bot))
