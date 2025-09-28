import discord
from discord.ext import commands
from discord.ext.commands import Bot, Context

LONG_HELP_TEXT = """
Generate a non-paywalled link from an existing URL using 12ft.io and web.archive.org
"""

SHORT_HELP_TEXT = """Generate non-paywalled link"""

class UnpaywallCog(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    def get_unpaywalled_link(self, url):
        """Generate alternative links for bypassing paywalls."""
        services = {
            "🔓 12ft.io": f"https://12ft.io/{url}",
            "📅 Web Archive": f"https://web.archive.org/web/{url}"
        }
        return services

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def unpaywall(self, ctx: Context, url: str):
        if not url.startswith("http") and not url.startswith("https"):
            await ctx.send("Please provide a valid URL.")

        services = self.get_unpaywalled_link(url)

        embed = discord.Embed(title="Non-Paywalled Links", color=0x3498db)
        for name, link in services.items():
            embed.add_field(name=name, value=f"[Click Here]({link})", inline=False)

        await ctx.reply(embed=embed)

async def setup(bot: Bot):
    await bot.add_cog(UnpaywallCog(bot))
