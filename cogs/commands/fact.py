import random
from pathlib import Path

import yaml
from discord.ext import commands
from discord.ext.commands import Bot, Context

from utils import get_name_string

LONG_HELP_TEXT = """
Selects a random "interesting" "fact".
"""

SHORT_HELP_TEXT = """Information!"""
FACT_LOCATION = Path("resources") / "fact.yaml"


def load_facts():
    with open(FACT_LOCATION, "r") as file:
        return yaml.full_load(file).get("facts")


class Fact(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.options = load_facts()

    @commands.command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def fact(self, ctx: Context):
        display_name = get_name_string(ctx.message)
        await ctx.send(f"{display_name}: {random.choice(self.options)}")


def setup(bot: Bot):
    bot.add_cog(Fact(bot))
