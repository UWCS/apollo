import random
from pathlib import Path

import requests
import yaml
from discord import Colour, Embed
from discord.ext import commands
from discord.ext.commands import Bot, Context

from utils import get_name_string
from utils.utils import user_is_irc_bot

LONG_HELP_TEXT = """
Selects a random "interesting" "fact".
"""

SHORT_HELP_TEXT = """Information!"""
FACT_LOCATION = Path("resources") / "fact.yaml"


def load_facts():
    with open(FACT_LOCATION, "r") as file:
        y = yaml.full_load(file)
        return y.get("facts"), y.get("fact-endpoint")


class Fact(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.options, self.endpoint = load_facts()

    def get_online_fact(self):
        r = requests.get(self.endpoint)
        if r.ok:
            return r.json()
        else:
            return None

    @commands.command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def fact(self, ctx: Context):
        display_name = get_name_string(ctx.message)
        if json := self.get_online_fact():
            if user_is_irc_bot(ctx):
                await ctx.send(
                    f"{display_name}: {json['text']} (from <{json['source']}>)"
                )
            else:
                embed = Embed(
                    title=json["text"],
                    description=f'[{json["source"]}]({json["source"]})',
                    colour=Colour.random(),
                ).set_footer(text=json["index"])
                await ctx.send(embed=embed)
        else:
            await ctx.send(f"{display_name}: {random.choice(self.options)}")


async def setup(bot: Bot):
    await bot.add_cog(Fact(bot))
