import random
import subprocess

from discord.ext import commands
from discord.ext.commands import Bot, Context

ZED0_HELP_TEXT = """Very important command."""
FAUX_HELP_TEXT = """A member of the Rust evangelical strike force."""
GO_HELP_TEXT = """The eternal #cs meme."""
DUNNO_HELP_TEXT = """¯\\_(ツ)_/¯"""
RUST_HELP_TEXT = """And if you gaze long into RUST, the RUST also gazes into you."""
PR_HELP_TEXT = """You know what to do"""
ISSUE_HELP_TEXT = """You know what you want someone else to do"""
BLUESHELL_HELP_TEXT = """!blueshell"""
AWOO_HELP_TEXT = """Tails and that"""
SINJO_HELP_TEXT = """o-o"""
SERVERS_HELP_TEXT = """List of our multiplayer servers"""
HASKELL_HELP_TEXT = """#notacult"""
PING_HELP_TEXT = """Pong!"""
XY_HELP_TEXT = """The XY problem is asking about your attempted solution rather than your actual problem."""
ASK_TO_ASK_HELP_TEXT = """Don't ask to ask - just ask."""


class Misc(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.version = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True
        ).stdout.decode()

    @commands.command(help=ZED0_HELP_TEXT, brief=ZED0_HELP_TEXT)
    async def zed0(self, ctx: Context):
        await ctx.send("¬_¬")

    @commands.command(help=FAUX_HELP_TEXT, brief=FAUX_HELP_TEXT)
    async def faux(self, ctx: Context):
        await ctx.send("RUST")

    @commands.command(help=GO_HELP_TEXT, brief=GO_HELP_TEXT)
    async def go(self, ctx: Context):
        await ctx.send("lol no generics")

    @commands.command(help=DUNNO_HELP_TEXT, brief=DUNNO_HELP_TEXT)
    async def dunno(self, ctx: Context):
        await ctx.send("¯\\_(ツ)_/¯")

    @commands.command(help=RUST_HELP_TEXT, brief=RUST_HELP_TEXT)
    async def rust(self, ctx: Context):
        await ctx.send("FAUX")

    @commands.command(help=PR_HELP_TEXT, brief=PR_HELP_TEXT)
    async def pr(self, ctx: Context):
        await ctx.send("You can make a pull request for that!")

    @commands.command(help=ISSUE_HELP_TEXT, brief=ISSUE_HELP_TEXT)
    async def issue(self, ctx: Context):
        await ctx.send("You can submit an issue for that!")

    @commands.command(help=BLUESHELL_HELP_TEXT, brief=BLUESHELL_HELP_TEXT)
    async def blueshell(self, ctx: Context):
        await ctx.send(
            "<:blueshell:541726526543101973> Thank you RNGesus for the £5 donation! <:blueshell:541726526543101973>"
        )

    @commands.command(help=AWOO_HELP_TEXT, brief=AWOO_HELP_TEXT)
    async def awoo(self, ctx: Context):
        await ctx.send("Aw{}~".format("o" * random.randrange(2, 5)))

    @commands.command(help=SINJO_HELP_TEXT, brief=SINJO_HELP_TEXT)
    async def sinjo(self, ctx: Context):
        await ctx.send(":neutral_face:")

    @commands.command(help=SERVERS_HELP_TEXT, brief=SERVERS_HELP_TEXT)
    async def servers(self, ctx: Context):
        await ctx.send(
            """:video_game: Running Servers :video_game:
We have some permanently running servers:

:ice_cube: Vanilla Minecraft :ice_cube:
We have a minecraft 1.16.4 server running at:
`minecraft.uwcs.co.uk`

:crossed_swords: Terraria :crossed_swords:
We have a Terraria 1.4.1.2 server running at:
`terraria.uwcs.co.uk:7777`"""
        )

    @commands.command(help=HASKELL_HELP_TEXT, brief=HASKELL_HELP_TEXT)
    async def haskell(self, ctx: Context):
        await ctx.send("https://www.youtube.com/watch?v=FYFhN_0QhfQ")

    @commands.command(help=PING_HELP_TEXT, brief=PING_HELP_TEXT)
    async def ping(self, ctx: Context):
        await ctx.send(":ping_pong:")

    @commands.command(brief="Apollo's current version")
    async def version(self, ctx: Context):
        """Print the SHA1 hash of HEAD in the deployed Apollo repository."""
        await ctx.send(self.version)

    @commands.command(aliases=["xyproblem"], help=XY_HELP_TEXT, brief=XY_HELP_TEXT)
    async def xy(self, ctx: Context):
        await ctx.send("https://xyproblem.info/")

    @commands.command(
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
        help=ASK_TO_ASK_HELP_TEXT,
        brief=ASK_TO_ASK_HELP_TEXT,
    )
    async def ask_to_ask(self, ctx: Context):
        await ctx.send("https://dontasktoask.com/")


def setup(bot: Bot):
    bot.add_cog(Misc(bot))
