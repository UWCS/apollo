import random

from discord.ext import commands
from discord.ext.commands import Context, Bot

LONG_HELP_TEXT = """
Selects a random "interesting" "fact".
"""

SHORT_HELP_TEXT = """Information!"""


class Fact:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.options = [
            "The billionth digit of Pi is 9.",
            "Humans can survive underwater. But not for very long.",
            "A nanosecond lasts one billionth of a second.",
            "Honey does not spoil.",
            "The atomic weight of Germanium is 72.64.",
            "An ostrich's eye is bigger than its brain.",
            "Rats cannot throw up.",
            "Iguanas can stay underwater for 28.7 minutes.",
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
            "Polymerase I polypeptide A is a human gene. The shortened gene name is POLR1A",
            "The Sun's mass is 330,330 times larger than Earth's and has a volume 1.3 million times larger.",
            "Dental floss has superb tensile strength.",
            "One comes before two comes before 60 comes after 12 comes before six trillion comes after 504.",
            "The first person to prove that cow's milk is drinkable was very, very thirsty.",
            "Vulcanologists are experts in the study of volcanoes.",
            "In Victorian England, a commoner was not allowed to look directly at the Queen, due to a belief at the time that the poor had the ability to steal thoughts. Science now believes that less than 4% of poor people are able to do this.",
            "In Greek myth, Prometheus stole fire from the Gods and gave it to humankind.",
            "The Schrödinger's cat paradox outlines a situation in which a cat in a box must be considered, for all intents and purposes, simultaneously alive and dead.",
            "The plural of 'surgeon general' is 'surgeons general'.",
            "Contrary to popular belief, the Eskimo does not have one hundred different words for snow.",
            "Diamonds are made when coal is put under intense pressure.",
            "Halley's Comet can be viewed orbiting Earth every 76 years.",
            "The first commercial airline flight took to the air in 1914.",
            "Edmund Hillary was the first person to climb Mount Everest",
            "Apollo is the best bot.",
            "Apollo is far superior to the irc bot."]

    @commands.command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def fact(self, ctx: Context):
        await ctx.send(f'<@{ctx.message.author.id}>: {random.choice(options)}')


def setup(bot: Bot):
    bot.add_cog(Fact(bot))
