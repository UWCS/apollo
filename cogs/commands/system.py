from discord.ext import commands
from discord.ext.commands import Bot, Context
from config import CONFIG
import aiohttp
from os import environ
import logging
import sys
import discord
import platform


class System(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.api_key = CONFIG.PORTAINER_API_KEY
        try:
            with open(".version", "r") as f:
                self.version_from_file = f.read()
        except FileNotFoundError:
            logging.error("Could not load git revision from file")
            self.version_from_file = None

    @commands.hybrid_command()
    async def info(self, ctx: Context):
        """Info about Apollo's build and environment"""
        # The below works, but the labels reported by the API are often out of date
        # for reasons I cannot figure out. TODO figure it out.
        url = (
            "https://portainer.uwcs.co.uk/api/endpoints/2/docker/containers/apollo/json"
        )
        headers = {"X-API-Key": f"{CONFIG.PORTAINER_API_KEY}"}
        async with aiohttp.ClientSession(headers=headers) as session:
            resp = await session.get(url)
            if not resp.ok:
                raise Exception("Could not reach Portainer API")
            content = await resp.json()

        version = content["Config"]["Labels"]["org.opencontainers.image.revision"]
        built = content["Config"]["Labels"]["org.opencontainers.image.created"]
        description = content["Config"]["Labels"][
            "org.opencontainers.image.description"
        ]
        py_version = platform.python_version()
        dpy_version = discord.__version__
        reply = f"Apollo, {description}\nBuilt from Git revision {version[:8]} on {built[0:10]} {built[11:19]}\nPython {py_version}, discord.py {dpy_version} "
        await ctx.reply(reply)

    @commands.hybrid_command()
    async def version(self, ctx: Context):
        """Get Apollo's version"""
        if self.version_from_file:
            await ctx.reply(self.version_from_file)
        else:
            await ctx.reply("Could not find version")


async def setup(bot: Bot):
    url = "https://portainer.uwcs.co.uk/api/endpoints/2/docker/containers/apollo/json"
    headers = {"X-API-Key": f"{CONFIG.PORTAINER_API_KEY}"}
    async with aiohttp.ClientSession(headers=headers) as session:
        resp = await session.get(url)
    match (resp.ok, environ.get("CONTAINER") is not None):
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
