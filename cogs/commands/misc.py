import random

from discord.ext import commands
from discord.ext.commands import Bot, Context


class Misc(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_command()
    async def zed0(self, ctx: Context):
        """Very important command."""
        await ctx.send("¬_¬")

    @commands.hybrid_command()
    async def faux(self, ctx: Context):
        """A member of the Rust evangelical strike force."""
        await ctx.send("RUST")

    @commands.hybrid_command()
    async def joey(self, ctx: Context):
        """Another member of the Rust evangelical strike force."""
        await ctx.send("RUST")

    @commands.hybrid_command()
    async def go(self, ctx: Context):
        """The eternal #cs meme."""
        await ctx.send(
            "Why did the Gopher become a programmer? Because it had a knack for golang out of its way to solve problems inefficiently!"
        )

    @commands.hybrid_command()
    async def rust(self, ctx: Context):
        """And if you gaze long into RUST, the RUST also gazes into you."""
        names = ["JOEY", "FAUX"]
        await ctx.send(random.choice(names))

    @commands.hybrid_command()
    async def pr(self, ctx: Context):
        """You know what to do"""
        await ctx.send(
            "You can make a pull request for that! (<https://github.com/UWCS/apollo/pulls>)"
        )

    @commands.hybrid_command()
    async def issue(self, ctx: Context):
        """You know what you want someone else to do"""
        await ctx.send(
            "You can submit an issue for that! (<https://github.com/UWCS/apollo/issues>)"
        )

    @commands.hybrid_command()
    async def merge(self, ctx: Context):
        """You know what you've already done, but need someone else to approve"""
        await ctx.send("_**JOOOOOOOOOHN!**_")

    @commands.hybrid_command()
    async def deploy(self, ctx: Context):
        """Push the button"""
        await ctx.send("Please be patient.")

    @commands.hybrid_command()
    async def blueshell(self, ctx: Context):
        """!blueshell"""
        await ctx.send(
            "<:blueshell:541726526543101973> Thank you RNGesus for the £5 donation! <:blueshell:541726526543101973>"
        )

    @commands.hybrid_command()
    async def awoo(self, ctx: Context):
        """Tails and that"""
        await ctx.send("Aw{}~".format("o" * random.randrange(2, 5)))

    @commands.hybrid_command()
    async def sinjo(self, ctx: Context):
        """o-o"""
        await ctx.send(":neutral_face:")

    @commands.hybrid_command()
    async def haskell(self, ctx: Context):
        """#notacult"""
        await ctx.send("https://www.youtube.com/watch?v=FYFhN_0QhfQ")

    @commands.hybrid_command()
    async def ping(self, ctx: Context):
        """Pong!"""
        await ctx.send(":ping_pong:")

    @commands.hybrid_command()
    async def pong(self, ctx: Context):
        """Ping!"""
        await ctx.send("<:pong_ping:1009151221338230875>")

    @commands.hybrid_command(aliases=["xyproblem"])
    async def xy(self, ctx: Context):
        """The XY problem is asking about your attempted solution rather than your actual problem."""
        await ctx.send("https://xyproblem.info/")

    @commands.hybrid_command(
        aliases=[
            "asktoask",
            "a2a",
            "ask2ask",
            "da2a",
            "dont_ask_to_ask",
            "dontask2ask",
            "don't_ask_to_ask",
            "don'tasktoask",
        ],
    )
    async def ask_to_ask(self, ctx: Context):
        """Don't ask to ask - just ask."""
        await ctx.send("https://dontasktoask.com/")

    @commands.hybrid_command()
    async def github(self, ctx: Context):
        """Link the Apollo GitHub repository"""
        await ctx.send("https://github.com/UWCS/apollo")

    @commands.hybrid_command()
    async def babbage(self, ctx: Context):
        await ctx.send(
            "Pray, Mr. Babbage, if you put into the machine wrong figures, will the right answers come out?"
        )


async def setup(bot: Bot):
    await bot.add_cog(Misc(bot))
