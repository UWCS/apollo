import os
from datetime import datetime

import matplotlib
from discord.ext import commands
from discord.ext.commands import Context, Bot, clean_content
from discord.file import File
from skimage import io, color, img_as_float

from config import CONFIG
from utils.aliases import get_name_string

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

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
        await ctx.trigger_typing()
        print(message)
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
        plt.rc("font", **{"family": "serif", "serif": ["Palatino"], "size": 16})
        plt.axis("off")

        # Generate the filename
        filename = (
            tex_code
            + "-"
            + str(hex(int(datetime.utcnow().timestamp()))).lstrip("0x")
            + ".png"
        ).replace(" ", "")
        path_png = "{path}/{filename}".format(
            path=CONFIG["FIG_SAVE_PATH"].rstrip("/"), filename=filename
        )
        path_jpg = path_png.replace(".png", ".jpg")
        try:
            # Plot the latex and save it.
            plt.text(0, 1, tex_code, color="white")
            plt.savefig(path_png, dpi=300, bbox_inches="tight", transparent=True)
        except RuntimeError as r:
            # Failed to render latex. Report error
            print(r)
            await ctx.send("Unable to render LaTeX. Please check that it's correct")
        else:
            # Generate a mask of the transparent regions in the image
            img_arr = img_as_float(io.imread(path_png))
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

            # Save the image, delete the PNG and set the permissions for the JPEG
            io.imsave(path_jpg, img_cropped, quality=100)
            os.chmod(path_jpg, 0o644)
            os.remove(path_png)

            # Load the image as a file to be attached to an image
            img_file = File(path_jpg, filename="tex_output.jpg")
            display_name = get_name_string(ctx.message)
            await ctx.send(f"Here you go, {display_name}! :abacus:", file=img_file)


def setup(bot: Bot):
    bot.add_cog(Tex(bot))
