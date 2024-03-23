from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content

LONG_HELP_TEXT = """
Summon the Joel of the Tech.
"""


SHORT_HELP_TEXT = """Joel Tech is here to help"""


class JoelTech(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def joeltech(self, ctx: Context, *, message: clean_content):
        await ctx.send("<:joel_tech:1217584610029076480>")


async def setup(bot: Bot):
    await bot.add_cog(JoelTech(bot))
