import io
import logging
from datetime import datetime

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content
from discord.file import File
from skimage import color, img_as_float, io as skio

from utils import get_name_string

matplotlib.use("Agg")


# Discord background colour
IMAGE_BACKGROUND = [(54 / 255), (58 / 255), (64 / 255)]

LONG_HELP_TEXT = """
Render a LaTeX maths expression to an image and show it in-line.

The expression _must_ be formatted in a LaTeX math environment inside of an inline code block (wrapped in ``). An example is:

`$e = mc^2$`
"""

SHORT_HELP_TEXT = """Display LaTeX formatted maths."""


class Tex(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def tex(self, ctx: Context, *message: clean_content):
        await ctx.typing()
        # Input filtering
        if not message:
            await ctx.send("Your message contained nothing to render")

        if message[0] == "```tex":
            message = ("```", *message[1:])
        combined = " ".join([x.lstrip("@") for x in message])
        if combined[0] != "`" or combined[-1] != "`":
            await ctx.send("Please place your input in an inline code block")
            return

        tex_code = combined.lstrip("`").rstrip("`")
        # May want to consider enforcing the $message$ requirement here
        # May also want to disallow/convert $$message$$ environments here

        # Matplotlib preamble
        plt.clf()
        plt.rc("text", usetex=True)
        plt.rc("text.latex", preamble=r"\usepackage{amsmath}")
        plt.rc("font", **{"family": "serif", "serif": ["Palatino"], "size": 16})
        plt.axis("off")

        # Generate the filename
        filename = (
            tex_code
            + "-"
            + str(hex(int(datetime.utcnow().timestamp()))).lstrip("0x")
            + ".png"
        ).replace(" ", "")
        img = io.BytesIO()
        try:
            # Plot the latex and save it.
            plt.text(0, 1, tex_code, color="white")
            plt.savefig(img, dpi=300, bbox_inches="tight", transparent=True, format="png")
        except RuntimeError as r:
            # Failed to render latex. Report error
            logging.error(r)
            await ctx.send("Unable to render LaTeX. Please check that it's correct")
            raise r
        else:
            # Generate a mask of the transparent regions in the image
            img_arr = img_as_float(skio.imread(img))
            transparent_mask = np.array([1, 1, 1, 0])
            img_mask = np.abs(img_arr - transparent_mask).sum(axis=2) < 1

            # Generate the bounding box for the mask
            mask_coords = np.array(np.nonzero(~img_mask))
            top_left = np.min(mask_coords, axis=1) - [15, 15]
            bottom_right = np.max(mask_coords, axis=1) + [15, 15]

            # Crop the image and add a background layer
            img_cropped = img_arr[
                top_left[0] : bottom_right[0], top_left[1] : bottom_right[1]
            ]
            img_cropped = color.rgba2rgb(img_cropped, background=IMAGE_BACKGROUND)

            # Update img to match crop
            img = io.BytesIO()
            skio.imsave(img, img_cropped, format='png')
            img.seek(0)

            # Load the image as a file to be attached to an image
            img_file = File(img, filename=filename)
            display_name = get_name_string(ctx.message)
            await ctx.send(f"Here you go, {display_name}! :abacus:", file=img_file)


async def setup(bot: Bot):
    await bot.add_cog(Tex(bot))
