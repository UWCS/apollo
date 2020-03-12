import discord
from discord.ext import commands
from discord.ext.commands import Bot, Context


class Roles(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.Cog.listener(name="on_reaction_add")
    async def on_reaction_add(self, reaction, user):
        await reaction.message.channel.send("owo")

    @commands.Cog.listener(name="on_reaction_remove")
    async def on_reaction_remove(self, reaction, user):
        await reaction.message.channel.send("uwu")


def setup(bot: Bot):
    bot.add_cog(Roles(bot))
