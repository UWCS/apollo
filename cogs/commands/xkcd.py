import json
import logging
import random
from io import BytesIO

import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands import Bot, Context

from config import CONFIG

LONG_HELP_TEXT = """
For all your xkcd needs

Use /xkcd <comicID> to gets the image of a comic with a specific ID.
Or just use /xkcd to get a random comic.
If an invalid arguement is made a random comic is returned
"""

SHORT_HELP_TEXT = "For all your xkcd needs"


class XKCD(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def xkcd(self, ctx: Context, comic_id: int | None = None):
        """gets either a random comic or a specific one"""
        max_comic_id = await self.get_recent_comic()  # gets the most recent comic's id
        if max_comic_id is None:
            return await ctx.reply("Error: could not get most recent comic")

        # If unspecified, randomize
        if comic_id is None:
            comic_id = random.randint(1, max_comic_id)
        # If invalid id then generate a random valid one
        elif comic_id <= 0 or comic_id > max_comic_id:
            return await ctx.reply("Error: invalid comic id")

        comic_return = await self.get_comic(comic_id)  # get the raw json of the comic
        if comic_return is None:
            return await ctx.reply(f"Error: could not get comic {comic_id}")

        comic_json = json.loads(comic_return)  # convert into readable
        comic_img = await self.get_comic_image(comic_json["img"])
        if comic_img is None:
            return await ctx.reply("Error: could not get comic image")

        # reply with comic title, url, and image
        comic_title = comic_json["safe_title"]
        await ctx.reply(
            f"**{comic_title}**, available at <https://xkcd.com/{comic_id}/>",
            file=comic_img,
        )

    async def get_comic(self, comic_id: int) -> str | None:
        """gets a comic with a specific id"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://xkcd.com/{comic_id}/info.0.json"
            ) as response:
                if response.status == 200:
                    logging.info("successfully got comic:" + str(comic_id))
                    return await response.read()
                else:
                    logging.info("failed to get comic: " + str(comic_id))
                    return None

    async def get_recent_comic(self) -> int | None:
        """gets the most recent comic id"""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://xkcd.com/info.0.json") as response:
                if response.status == 200:
                    logging.info("successfully got moset recent comic")
                    xkcd_response = json.loads(await response.read())
                    return xkcd_response["num"]
                else:
                    logging.info("failed to get comic")
                    return None

    async def get_comic_image(self, url: str) -> str | None:
        """gets an image in the form of a discord file"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    logging.info("successfully got comic image")
                    return discord.File(
                        BytesIO(await response.read()), filename="image.png"
                    )
                else:
                    logging.info("failed to get comic image")
                    return None


async def setup(bot: Bot):
    await bot.add_cog(XKCD(bot))
