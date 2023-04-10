from discord.ext import commands
from discord.ext.commands import Bot, Context
from config import CONFIG
import aiohttp
from os import environ
import logging


class System(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.api_key = CONFIG.PORTAINER_API_KEY

    @commands.hybrid_command()
    async def version(self, ctx: Context):
        """Get Apollo's current version"""
        url = (
            "https://portainer.uwcs.co.uk/api/endpoints/2/docker/containers/apollo/json"
        )
        headers = {"X-API-Key": f"{CONFIG.PORTAINER_API_KEY}"}
        async with aiohttp.ClientSession(headers=headers) as session:
            resp = await session.get(url)
            if not resp.ok:
                raise Exception("Could not reach Portainer API")
            content = await resp.json()

        git_rev = content["Labels"]["org.opencontainers.image.revision"]
        built = content["Labels"]["org.opencontainers.image.created"]
        reply = f"Apollo, built from Git revision {git_rev[:8]} on {built[0:10]} {built[11:19]}"
        await ctx.reply(reply)


# attempt to get at API, if we can't then don't load the cog
async def setup(bot: Bot):
    url = "https://portainer.uwcs.co.uk/api/endpoints/2/docker/containers/apollo/json"
    headers = {"X-API-Key": f"{CONFIG.PORTAINER_API_KEY}"}
    async with aiohttp.ClientSession(headers=headers) as session:
        resp = await session.get(url)
    match (resp.ok, environ.get is not None):
        case (True, True):
            await bot.add_cog(System(bot))
        case (True, False):
            logging.error(
                "Can reach Portainer API but not running in container. Not loading system cog."
            )
        case (False, True):
            logging.error(
                "Running in container but can't reach Portainer API. Not loading system cog."
            )
        case (False, False):
            logging.error("Not loading system cog.")
