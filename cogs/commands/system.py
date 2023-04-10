from discord.ext import commands
from discord.ext.commands import Bot, Context
from config import CONFIG
import aiohttp
from os import environ
import logging
import discord
import platform
from datetime import datetime
from typing import Any

APOLLO_URL = (
    "https://portainer.uwcs.co.uk/api/endpoints/2/docker/containers/apollo/json"
)


class System(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

        try:
            with open(".version", "r") as f:
                content = f.readlines()
                self.version_from_file = content[0].rstrip()
                self.build_timestamp_from_file = content[1].rstrip()
        except FileNotFoundError:
            logging.error("Could not load git revision from file")
            self.version_from_file = None
            self.build_timestamp_from_file = None

    @commands.hybrid_command()
    async def info(self, ctx: Context[Bot]):
        json = await self.get_docker_json()
        if json is None:
            return

        # these are likely to be outdated, so we don't use them.
        # version = json["Config"]["Labels"]["org.opencontainers.image.revision"]
        # built = json["Config"]["Labels"]["org.opencontainers.image.created"]

        version = self.version_from_file
        built = self.build_timestamp_from_file

        description: str = json["Config"]["Labels"][
            "org.opencontainers.image.description"
        ]

        py_version = platform.python_version()
        dpy_version = discord.__version__

        # the timestamp docker gives does not conform to ISO.
        # we strip the fractional secconds and add the suffix which assumes UTC (may cause issues in summer)
        timestamp: str = json["State"]["StartedAt"]
        started = datetime.fromisoformat(timestamp.split(".")[0])
        uptime = datetime.now() - started

        if version and built:
            reply = f"""Apollo, {description}\n
Built from Git revision {version[:8]} on {built[0:10]} {built[11:19]}
Python {py_version}, discord.py {dpy_version} 
Started {started} (uptime {uptime})"""

        else:
            reply = f"""Apollo, {description}\n
Could not get build information
Python {py_version}, discord.py {dpy_version} 
Started {started} (uptime {uptime})"""
        await ctx.reply(reply)

    @commands.hybrid_command()
    async def version(self, ctx: Context[Bot]):
        """Get Apollo's version"""
        if self.version_from_file:
            await ctx.reply(self.version_from_file)
        else:
            await ctx.reply("Could not find version")

    @staticmethod
    async def get_docker_json() -> dict[Any, Any] | None:
        headers = {"X-API-Key": f"{CONFIG.PORTAINER_API_KEY}"}
        async with aiohttp.ClientSession(headers=headers) as session:
            resp = await session.get(APOLLO_URL)
            if not resp.ok:
                logging.error("Could not reach Portainer API")
                return None
            return await resp.json()


async def setup(bot: Bot):
    url = "https://portainer.uwcs.co.uk/api/endpoints/2/docker/containers/apollo/json"
    headers = {"X-API-Key": f"{CONFIG.PORTAINER_API_KEY}"}
    async with aiohttp.ClientSession(headers=headers) as session:
        resp = await session.get(url)
    match (resp.ok, (environ.get("CONTAINER") is not None)):
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
        case _:
            logging.error("Not loading system cog.")
