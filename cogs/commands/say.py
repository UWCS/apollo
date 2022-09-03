import discord
from discord import AllowedMentions, app_commands
from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content

LONG_HELP_TEXT = """
Make the bot repeat after you.
"""

SHORT_HELP_TEXT = """Make the bot repeat after you."""


class Say(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @app_commands.command(name="say", description=SHORT_HELP_TEXT)
    async def say_slash(self, int: discord.Interaction, message: str):
        await int.response.send_message(
            message, allowed_mentions=AllowedMentions.none()
        )

    @commands.command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def say(self, ctx: Context, *message: clean_content):
        await ctx.send(" ".join([x.lstrip("@") for x in message]))


async def setup(bot: Bot):
    await bot.add_cog(Say(bot))
