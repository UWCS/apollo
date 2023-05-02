import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content

from config import CONFIG
from utils import get_json_from_url as json_url

LONG_HELP_TEXT = "Lists all the servers running on PufferPanel"

SHORT_HELP_TEXT = "Server info from PufferPanel"


class PufferPanel(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def pufferpanel(self, ctx: Context):
        info = await self.get_servers()
        await ctx.send(info)

    async def get_servers(self) -> str:
        headers = {"Authorization": f"Bearer {await self.get_oauth_token()}"}
        json = await json_url(
            "https://pufferpanel.uwcs.co.uk/api/servers?name=*", headers
        )
        out = []
        out.append("🛠 Manage servers at: https://pufferpanel.uwcs.co.uk/ \n")
        for server in json["servers"]:
            name = server["name"]
            ip = f"lovelace.uwcs.co.uk:{server['port']}"

            type = []
            for string in server["type"].split("-"):
                type.append(string.capitalize())
            type = " ".join(type)

            out.append(f"**{name}**")
            out.append(f" > {type}")
            out.append(f" > `{ip}`")
            out.append(f"")
        return "\n".join(out[:-1])

    async def get_oauth_token(_self):
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
                return (await response.json())["access_token"]


async def setup(bot: Bot):
    await bot.add_cog(PufferPanel(bot))
