import sqlite3

from discord.ext import commands
from discord.ext.commands import Bot, CommandInvokeError, Context, clean_content
from discord.ext.commands.errors import CommandError
from sqlalchemy.exc import SQLAlchemyError

from models import db_session
from models.votes import DiscordVoteMessage
from voting.discord_interfaces.discord_base import DiscordBase
from voting.splitutils import split_args

LONG_HELP_TEXT = """
Allows running of various types of votes: FPTP, STV, etc. (WIP)
"""

SHORT_HELP_TEXT = """Allows running of various types of votes"""


class Vote(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    # @commands.hybrid_group(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    # async def vote(self, ctx: Context):
    #     if not ctx.invoked_subcommand:
    #         await ctx.send("Subcommand not found")

    # @vote.command(
    @commands.hybrid_command(
        help="Run basic poll with given options, votes are visible. Provide options as new-line, semi-colon, comma or space separated options, the first will be taken as the title. If you wish to use a separator in an option, escape it with a backslash `\\`.",
        brief="Runs basic poll with visible votes. Can use `\\n`, `;`, `,` or ` ` separators. Escape with `\\`",
        aliases=["poll"],
        usage="<title>; [<option 1>; <option 2>; [...]]",
    )
    # async def basic(self, ctx: Context, *, args: str):
    async def vote(self, ctx: Context, *, args: str):
        print(args)
        args = await clean_content().convert(ctx, args)
        # noinspection PyTypeChecker
        choices = split_args(args)
        # If just one choice, split might just give as a per letter list
        if len(choices) == len(args):
            choices = [args]
        print(choices)
        await DiscordBase(self.bot).create_vote(ctx, choices)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()

        vote_msgs = db_session.query(DiscordVoteMessage).all()
        threshold_time = datetime.now().astimezone(timezone.utc) - timedelta(months=1)
        for dvm in vote_msgs:
            channel = self.bot.get_channel(dvm.channel_id)
            msg = await channel.fetch_message(dvm.message_id)
            if msg is None or msg.created_at < threshold_time:
                print("Ending", msg)
                await msg.edit(view=None)
            else:
                await msg.edit(
                    view=DiscordBase(self.bot).recreate_view(dvm.vote_id, msg, dvm)
                )


async def setup(bot: Bot):
    await bot.add_cog(Vote(bot))
