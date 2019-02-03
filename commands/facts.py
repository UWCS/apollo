import random

from discord.ext import commands
from discord.ext.commands import Context, Bot

LONG_HELP_TEXT = """
Selects a random "interesting" "fact".
"""

SHORT_HELP_TEXT = """Information!"""


class Facts:
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def facts(self, ctx: Context):
        options = [
            "The billionth digit of Pi is 9.",
            "Humans can survive underwater. But not for very long.",
            "A nanosecond lasts one billionth of a second.",
            "Honey does not spoil.",
            "The atomic weight of Germanium is 72.64.",
            "An ostrich's eye is bigger than its brain.",
            "Rats cannot throw up.",
            "Iguanas can stay underwater for twenty-eight point seven minutes.",
            "The moon orbits the Earth every 27.32 days.",
            "A gallon of water weighs 8.34 pounds.",
            "According to Norse legend, thunder god Thor's chariot was pulled across the sky by two goats.",
            "Tungsten has the highest melting point of any metal, at 3,410 degrees Celsius.",
            "Gently cleaning the tongue twice a day is the most effective way to fight bad breath.",
            "The Tariff Act of 1789, established to protect domestic manufacture, was the second statute ever enacted by the United States government.",
            "The value of Pi is the ratio of any circle's circumference to its diameter in Euclidean space.",
            "The Mexican-American War ended in 1848 with the signing of the Treaty of Guadalupe Hidalgo.",
            "In 1879, Sandford Fleming first proposed the adoption of worldwide standardized time zones at the Royal Canadian Institute.",
            "Marie Curie invented the theory of radioactivity, the treatment of radioactivity, and dying of radioactivity.",
            "Hot water freezes quicker than cold water.",
            "The situation you are in is very dangerous.",
            "Polymerase I polypeptide A is a human gene. The shortened gene name is POLR1A"]

        await ctx.send(f'<@{ctx.message.author.id}>: {random.choice(options)}')


def setup(bot: Bot):
    bot.add_cog(Flip(bot))
