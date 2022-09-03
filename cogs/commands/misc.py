import random
import subprocess

from discord.ext import commands
from discord.ext.commands import Bot, Context


class Misc(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.version = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True
        ).stdout.decode()

    @commands.hybrid_command()
    async def zed0(self, ctx: Context):
        """Very important command."""
        await ctx.send("¬_¬")

    @commands.hybrid_command()
    async def faux(self, ctx: Context):
        """A member of the Rust evangelical strike force."""
        await ctx.send("RUST")

    @commands.hybrid_command()
    async def go(self, ctx: Context):
        """The eternal #cs meme."""
        await ctx.send("lol no generics")

    @commands.hybrid_command()
    async def dunno(self, ctx: Context):
        """¯\\_(ツ)_/¯"""
        await ctx.send("¯\\_(ツ)_/¯")

    @commands.hybrid_command()
    async def rust(self, ctx: Context):
        """And if you gaze long into RUST, the RUST also gazes into you."""
        await ctx.send("FAUX")

    @commands.hybrid_command()
    async def pr(self, ctx: Context):
        """You know what to do"""
        await ctx.send("You can make a pull request for that!")

    @commands.hybrid_command()
    async def issue(self, ctx: Context):
        """You know what you want someone else to do"""
        await ctx.send("You can submit an issue for that!")

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
    async def servers(self, ctx: Context):
        """List of our multiplayer servers"""
        await ctx.send(
            """:video_game: Running Servers :video_game:
We have some permanently running servers:

:ice_cube: Minecraft for Minecraft Society :ice_cube:
A Minecraft survival server running at `warwickminecraft.uk`
"""
        )

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
        await ctx.send(":pong_ping:")

    @commands.hybrid_command(brief="Apollo's current version")
    async def version(self, ctx: Context):
        """Print the SHA1 hash of HEAD in the deployed Apollo repository."""
        await ctx.send(self.version)

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
