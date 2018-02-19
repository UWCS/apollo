from datetime import datetime, timedelta

import matplotlib.pyplot as plt
from discord import File
from discord.ext import commands
from discord.ext.commands import Context, Bot, CommandError, clean_content, BucketType
from matplotlib.dates import DayLocator, WeekdayLocator, MonthLocator, YearLocator, DateFormatter, date2num, \
    HourLocator, MinuteLocator
from sqlalchemy import func

from models import db_session, Karma as KarmaModel, KarmaChange

LONG_HELP_TEXT = """
Query and display the information about the karma topics on the UWCS discord server.
"""
SHORT_HELP_TEXT = """View information about karma topics."""


class KarmaError(CommandError):
    message = None

    def __init__(self, message=None, *args):
        self.message = message
        super().__init__(*args)


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
        top_karma = db_session.query(KarmaModel).order_by(KarmaModel.net_score.desc(), KarmaModel.name.asc()) \
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
        # Get the bottom 5 karma items
        top_karma = db_session.query(KarmaModel) \
            .order_by(KarmaModel.net_score.asc(), KarmaModel.name.asc()).limit(5).all()

        # Construct the appropriate response string
        result = f'The bottom {len(top_karma)} items and their scores are:\n\n'
        for karma in top_karma:
            latest_karma = db_session.query(KarmaChange).filter(KarmaChange.karma_id == karma.id) \
                .order_by(KarmaChange.created_at.desc()).first()
            result += f' • **{karma.name}** with a score of {latest_karma.score}\n'
        result += '\nWhere equal scores, karma is sorted alphabetically. :scales:'

        await ctx.send(result)

    @karma.command(help='Shows the top !5 most karma\'d topics')
    async def most(self, ctx: Context):
        # Get the 5 most karma'd items
        most_karma = db_session.query(KarmaModel) \
            .order_by(KarmaModel.total_karma.desc(), KarmaModel.name.asc()).limit(5).all()

        # Construct the response string
        result = f'The 5 most karma\'d topics and their total karma are:\n\n'
        for karma in most_karma:
            result += f' • **{karma.name}** being karma\'d a total number of {karma.total_karma} times\n'
        result += '\nWhere equal scores, karma is sorted alphabetically. :scales:'

        await ctx.send(result)

    @karma.command(help='Gives information about specified karma topics')
    async def info(self, ctx: Context, *args):
        await ctx.send('That command isn\'t implemented at the moment. :cry:')

    @karma.command(help='Plots the karma change over time of the specified karma', ignore_extra=True)
    @commands.cooldown(5, 60, BucketType.user)
    async def plot(self, ctx: Context, karma: clean_content):
        await ctx.trigger_typing()

        karma_stripped = karma.lstrip('@')
        karma_item = db_session.query(KarmaModel).filter(
            func.lower(KarmaModel.name) == func.lower(karma_stripped)).first()

        if karma_item:
            changes = db_session.query(KarmaChange).filter(KarmaChange.karma_id == karma_item.id) \
                .order_by(KarmaChange.created_at.asc()).all()

            if len(changes) < 10:
                plural = ''
                if len(changes) > 1:
                    plural = 's'

                raise KarmaError(
                    message=f'"{karma}" must have been karma\'d at least 10 times before a plot can be made (currently karma\'d {len(changes)} time{plural}). :chart_with_upwards_trend:')

            karma_timeline = changes[-1].local_time - changes[0].local_time

            print(karma_timeline)

            if karma_timeline < timedelta(hours=1):
                date_format = DateFormatter('%H:%M %d %b %Y')
                date_locator_major = MinuteLocator(interval=15)
                date_locator_minor = MinuteLocator()
            elif karma_timeline < timedelta(hours=6):
                date_format = DateFormatter('%H:%M %d %b %Y')
                date_locator_major = HourLocator()
                date_locator_minor = MinuteLocator(interval=15)
            elif karma_timeline < timedelta(days=7):
                date_format = DateFormatter('%d %b %Y')
                date_locator_major = DayLocator()
                date_locator_minor = HourLocator(interval=6)
            elif karma_timeline < timedelta(days=30):
                date_format = DateFormatter('%d %b %Y')
                date_locator_major = WeekdayLocator()
                date_locator_minor = DayLocator()
            elif karma_timeline < timedelta(days=365):
                date_format = DateFormatter('%B %Y')
                date_locator_major = MonthLocator()
                date_locator_minor = WeekdayLocator(interval=2)
            else:
                date_format = DateFormatter('%Y')
                date_locator_major = YearLocator()
                date_locator_minor = MonthLocator()

            scores = list(map(lambda k: k.score, changes))
            time = date2num(list(map(lambda k: k.local_time, changes)))

            filename = f'tmp/{karma_stripped}-{datetime.utcnow()}.png'

            # Plot the graph and save it to a png
            plt.rcParams.update({'figure.autolayout': True})
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.xaxis.set_major_locator(date_locator_major)
            ax.xaxis.set_minor_locator(date_locator_minor)
            ax.xaxis.set_major_formatter(date_format)
            ax.grid(b=True, which='minor', color='0.9', linestyle=':')
            ax.grid(b=True, which='major', color='0.5', linestyle='--')
            ax.set(xlabel='Time', ylabel='Karma',
                   xlim=[time[0] - ((time[-1] - time[0]) * 0.05), time[-1] + ((time[-1] - time[0]) * 0.05)])
            ax.plot_date(time, scores, '-', xdate=True)
            fig.autofmt_xdate()
            fig.savefig(filename, dpi=240, transparent=False)

            # Open a file pointer to send it in Discord
            plot_image = open(filename, mode='rb')
            plot = File(plot_image)
            await ctx.send(f'Here\'s the karma trend for "{karma}" over time', file=plot)
        else:
            # The item hasn't been karma'd
            result = f'"{karma_stripped}" hasn\'t been karma\'d yet. :cry:'
            await ctx.send(result)

    @plot.error
    async def plot_error_handler(self, ctx: Context, error: KarmaError):
        await ctx.send(error.message)

    @karma.command(help='Lists the reasons (if any) for the specific karma', ignore_extra=True)
    async def reasons(self, ctx: Context, karma: clean_content):
        karma_stripped = karma.lstrip('@')

        # Get the karma from the database
        karma_item = db_session.query(KarmaModel).filter(func.lower(KarmaModel.name) == func.lower(karma_stripped)).first()

        if karma_item:
            # Get all of the changes that have some reason
            karma_changes = db_session.query(KarmaChange).filter(KarmaChange.karma_id == karma_item.id,
                                                                 KarmaChange.reasons != []).all()
            # Flatten the reasons into a single list and sort it alphabetically
            reasons = [reason for sublist in [change.reasons for change in karma_changes] for reason in sublist]
            reasons = sorted(reasons, key=str.lower)

            # If there's at least one reason
            if reasons:
                # Handle the plurality of reason(s)
                plural = ''
                if len(reasons) > 1:
                    plural = 's'

                result = f'The reason{plural} for "{karma_stripped}" are as follows:\n\n'
                for reason in reasons:
                    result += f' • {reason}\n'
            else:
                result = f'There are no reasons down for that karma topic! :frowning:'

            await ctx.send(result)
        else:
            # The item hasn't been karma'd
            result = f'"{karma_stripped}" hasn\'t been karma\'d yet. :cry:'
            await ctx.send(result)


def setup(bot: Bot):
    bot.add_cog(Karma(bot))
