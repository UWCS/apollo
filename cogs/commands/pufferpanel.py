import asyncio
import logging

import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands import Bot, Context
from mcstatus import JavaServer

from config import CONFIG
from utils import get_json_from_url as json_url

LONG_HELP_TEXT = "Lists all the servers running on PufferPanel"

SHORT_HELP_TEXT = "Server info from PufferPanel"


class PufferPanel(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def pufferpanel(self, ctx: Context):
        async with ctx.typing():
            token = await self.get_oauth_token()
            if token == None:
                logging.error("Bad ID/Token for Pufferpanel in config.yaml")
                return
            headers = {"Authorization": f"Bearer {token}"}
            json = await json_url(
                "https://pufferpanel.uwcs.co.uk/api/servers?name=*", headers
            )

            out = []
            out.append("🛠 Manage servers at: https://pufferpanel.uwcs.co.uk/ \n")
            for server in json["servers"]:
                name = server["name"]

                ip_port = f"{server['node']['publicHost']}:{server['port']}"

                type = []
                for string in server["type"].split("-"):
                    type.append(string.capitalize())
                type = " ".join(type)

                # Reply Creation

                info = await self.get_server_info(name, type, ip_port)
                out.append(info)

        await ctx.reply("\n".join(out))

    async def get_oauth_token(self) -> str:
        client_id = CONFIG.PUFFERPANEL_CLIENT_ID
        client_secret = CONFIG.PUFFERPANEL_CLIENT_SECRET
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://pufferpanel.uwcs.co.uk/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": CONFIG.PUFFERPANEL_CLIENT_ID,
                    "client_secret": CONFIG.PUFFERPANEL_CLIENT_SECRET,
                },
            ) as response:
                return (await response.json()).get("access_token", None)

    async def get_server_info(self, name: str, type: str, ip_port: str):
        out = []
        match type:
            case "Minecraft Java":
                try:
                    server = await JavaServer.async_lookup(ip_port, 2)
                    status = await server.async_status()
                    if status.description:
                        motd = status.description
                    if status.players:
                        players = f"{status.players.online}/{status.players.max}"
                except:
                    logging.info(f"Couldn't Connect to MC Java - {ip_port}")
                if "motd" in locals():
                    out.append(f"**{name}** - {motd}")
                else:
                    out.append(f"**{name}**")
                out.append(f"> **{type}**")
                if "players" in locals():
                    out.append(f"> **Players:** {players}")

            case _:
                out.append(f"**{name}**")
                out.append(f"> **{type}**")

        out.append(f"> **IP:** `{ip_port}`")

        return "\n".join(out)


async def setup(bot: Bot):
    await bot.add_cog(PufferPanel(bot))
