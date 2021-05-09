from discord.ext.commands import Bot, Cog


class Moderation(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot


def setup(bot: Bot):
    bot.add_cog(Moderation(bot))
