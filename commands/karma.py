from discord.ext import commands
from discord.ext.commands import Context, Bot

from models import db_session, Karma as KarmaModel, KarmaChange

LONG_HELP_TEXT = """
Query and display the information about the karma topics on the UWCS discord server.
"""
SHORT_HELP_TEXT = """View information about karma topics."""


class Karma:
    def __init__(self, bot):
        self.bot = bot

    @commands.group(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def karma(self, ctx: Context):
        if not ctx.invoked_subcommand:
            await ctx.send("Subcommand not found")

    @karma.command(help='Shows the top 5 karma topics')
    async def top(self, ctx: Context):
        # Get the top 5 karma items
        top_karma = db_session.query(KarmaModel).order_by(KarmaModel.net_score.desc(), KarmaModel.name.asc())\
            .limit(5).all()

        # Construct the appropriate response string
        result = f'The top {len(top_karma)} items and their scores are:\n\n'
        for karma in top_karma:
            latest_karma = db_session.query(KarmaChange).filter(KarmaChange.karma_id == karma.id) \
                .order_by(KarmaChange.created_at.desc()).first()
            result += f' • **{karma.name}** with a score of {latest_karma.score}\n'
        result += '\nWhere equal scores, karma is sorted alphabetically. :scales:'

        await ctx.send(result)

    @karma.command(help='Shows the bottom 5 karma topics')
    async def bottom(self, ctx: Context):
        pass

    @karma.command(help='Gives information about specified karma topics')
    async def info(self, ctx: Context):
        pass

    @karma.command(help='Plots the karma change over time of the specified karma', ignore_extra=True)
    async def plot(self, ctx: Context, karma: str):
        pass

    @karma.command(help='Lists the reasons (if any) for the specific karma', ignore_extra=True)
    async def reasons(self, ctx: Context, karma: str):
        pass


def setup(bot: Bot):
    bot.add_cog(Karma(bot))
