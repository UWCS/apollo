import datetime
import json
import random
import re

import requests
from discord.ext import commands, tasks
from discord.ext.commands import Bot, Context

import utils

LONG_HELP_TEXT = """
For all your xkcd needs

Use /xkcd <comicID> to gets the image of a comic with a specific ID.
Use /xkcd search <query> to search for a comic by title.
Or just use /xkcd to get a random comic.
If an invalid arguement is made a random comic is returned
"""

SHORT_HELP_TEXT = "For all your xkcd needs"


class XKCD(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.comics = None

    @commands.hybrid_group(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
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

        comic_return = await utils.get_from_url(
            f"https://xkcd.com/{comic_id}/info.0.json"
        )  # get the raw json of the comic
        if comic_return is None:
            return await ctx.reply(f"Error: could not get comic {comic_id}")

        comic_json = json.loads(comic_return)  # convert into readable
        comic_img = await utils.get_file_from_url(comic_json["img"])
        if comic_img is None:
            return await ctx.reply("Error: could not get comic image")

        # reply with comic title, url, and image
        comic_title = comic_json["safe_title"]
        msg = f"**{comic_title}**, available at <https://xkcd.com/{comic_id}/>"
        await ctx.reply(msg, file=comic_img)
    
    @xkcd.command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def search(self, ctx: Context, query: str):
        """searches for a comic by title"""

        # Load comics if not already loaded
        if not self.comics:
            self.comics = await self.get_all_comics()
        # Okay something went wrong
        if not self.comics:
            return await ctx.reply("Error: could not get comics list")
        
        # Search for query in titles
        results = [f"{title} ({comic_id})" for comic_id, title in self.comics.items() if query.lower() in title.lower()]
        
        # Return results
        if not results:
            return await ctx.reply(f"No comics found with title containing '{query}'")
        
        ret_str = f"Found {len(results)} comics with title containing '{query}':\n" + "\n".join(results)

        return await ctx.reply(ret_str)
        

    async def get_recent_comic(self) -> int | None:
        """gets the most recent comic id"""
        xkcd_response = await utils.get_json_from_url("https://xkcd.com/info.0.json")
        if xkcd_response:
            return xkcd_response["num"]
        return None
    
    async def get_all_comics(self) -> dict[int, str] | None:
        """gets a dictionary of all comic ids and their titles"""
        
        # Pattern to match lines giving comic id and title
        pattern = re.compile(r'<a\s+href="/(\d+)/"[^>]*>(.*?)</a>')

        https_response = requests.get("https://xkcd.com/archive/")
        if https_response.status_code != 200:
            return None

        html_text = https_response.text
        lines = [line for line in html_text.splitlines() if line != '']
        results = [pattern.findall(item) for item in lines]

        # flatten results since findall returns list of tuples
        results = [match for sub in results for match in sub]

        # Create dictionary from list of tuples
        comics = {int(comic_id): title for comic_id, title in results}
        
        return comics
    
    @tasks.loop(time=datetime.time(hour=4, minute=0, tzinfo=datetime.timezone.utc))
    async def update_comics(self):
        """updates the comics dictionary daily"""

        xkcd_response = await utils.get_json_from_url("https://xkcd.com/info.0.json")
        if not xkcd_response:
            return None
        max_comic_id = sorted(self.comics.keys())[-1]

        # No new comics
        if xkcd_response["num"] == max_comic_id:
            return
        
        # Add any new comics since last update
        self.comics[xkcd_response["num"]] = xkcd_response["safe_title"]
        for comic_id in range(max_comic_id + 1, xkcd_response["num"]):
            comic_response = await utils.get_json_from_url(f"https://xkcd.com/{comic_id}/info.0.json")
            if comic_response:
                self.comics[comic_id] = comic_response["safe_title"]


async def setup(bot: Bot):
    await bot.add_cog(XKCD(bot))
