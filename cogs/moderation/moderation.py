from textwrap import dedent
from typing import Optional

from discord import Member
from discord.ext.commands import Bot, Cog, Context, Greedy, command
from discord.utils import get

from utils import format_list, is_compsoc_exec_in_guild


class Moderation(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot


def setup(bot: Bot):
    bot.add_cog(Moderation(bot))
