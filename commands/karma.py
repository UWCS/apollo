import matplotlib

from apollo import pluralise

matplotlib.use('Agg')

import os
from collections import defaultdict
from datetime import datetime, timedelta
from functools import reduce
from time import time
from typing import List, Dict

import matplotlib.pyplot as plt
from discord import Embed, Color, File
from discord.ext import commands
from discord.ext.commands import Context, Bot, CommandError, clean_content, BucketType, MissingRequiredArgument
from matplotlib.dates import DayLocator, WeekdayLocator, MonthLocator, YearLocator, DateFormatter, date2num, \
    HourLocator, MinuteLocator
from pytz import utc, timezone
from sqlalchemy import func

from config import CONFIG
from models import db_session, Karma as KarmaModel, KarmaChange

from utils import get_name_string

LONG_HELP_TEXT = """
Query and display the information about the karma topics on the UWCS discord server.
"""
SHORT_HELP_TEXT = """View information about karma topics."""


class KarmaError(CommandError):
    message = None

    def __init__(self, message=None, *args):
        self.message = message
        super().__init__(*args)


# Utility function to get the current system time in milliseconds
def current_milli_time():
    return int(round(time() * 1000))


# Utility coroutine to generate the matplotlib Figure object that can be manipulated by the calling function
async def plot_karma(karma_dict: Dict[str, List[KarmaChange]]) -> (str, str):
    # Error if there's no input data
    if len(karma_dict) == 0:
        return '', ''

    # Matplotlib preamble
    plt.rcParams.update({'figure.autolayout': True})
    fig, ax = plt.subplots(figsize=(8, 6))

    # Get the earliest and latest karma values fo
    earliest_karma = utc.localize(datetime.utcnow()).astimezone(timezone('Europe/London'))
    latest_karma = utc.localize(datetime(1970, 1, 1)).astimezone(timezone('Europe/London'))
    for key, changes in karma_dict.items():
        earliest_karma = changes[0].local_time if changes[0].local_time < earliest_karma else earliest_karma
        latest_karma = changes[-1].local_time if changes[-1].local_time >= latest_karma else latest_karma

    karma_timeline = latest_karma - earliest_karma

    # Determine the right graph tick positioning
    if karma_timeline <= timedelta(hours=1):
        date_format = DateFormatter('%H:%M %d %b %Y')
        date_locator_major = MinuteLocator(interval=15)
        date_locator_minor = MinuteLocator()
    elif karma_timeline <= timedelta(hours=6):
        date_format = DateFormatter('%H:%M %d %b %Y')
        date_locator_major = HourLocator()
        date_locator_minor = MinuteLocator(interval=15)
    elif karma_timeline <= timedelta(days=14):
        date_format = DateFormatter('%d %b %Y')
        date_locator_major = DayLocator()
        date_locator_minor = HourLocator(interval=6)
    elif karma_timeline <= timedelta(days=30):
        date_format = DateFormatter('%d %b %Y')
        date_locator_major = WeekdayLocator()
        date_locator_minor = DayLocator()
    elif karma_timeline <= timedelta(days=365):
        date_format = DateFormatter('%B %Y')
        date_locator_major = MonthLocator()
        date_locator_minor = WeekdayLocator(interval=2)
    else:
        date_format = DateFormatter('%Y')
        date_locator_major = YearLocator()
        date_locator_minor = MonthLocator()

    # Transform the karma changes into plottable values
    for karma, changes in karma_dict.items():
        scores = list(map(lambda k: k.score, changes))
        time = date2num(list(map(lambda k: k.local_time, changes)))

        # Plot the values
        ax.xaxis.set_major_locator(date_locator_major)
        ax.xaxis.set_minor_locator(date_locator_minor)
        ax.xaxis.set_major_formatter(date_format)
        ax.grid(b=True, which='minor', color='0.9', linestyle=':')
        ax.grid(b=True, which='major', color='0.5', linestyle='--')
        ax.set(xlabel='Time', ylabel='Karma',
               xlim=[time[0] - ((time[-1] - time[0]) * 0.05), time[-1] + ((time[-1] - time[0]) * 0.05)])
        line, = ax.plot_date(time, scores, '-', xdate=True)
        line.set_label(karma)

    # Create a legend if more than  1 line and format the dates
    if len(karma_dict.keys()) > 1:
        ax.legend()
    fig.autofmt_xdate()

    # Save the file to disk and set the right permissions
    filename = (''.join(karma_dict.keys()) + '-' + str(hex(int(datetime.utcnow().timestamp()))).lstrip('0x') + '.png') \
        .replace(' ', '')
    path = '{path}/{filename}'.format(path=CONFIG['FIG_SAVE_PATH'].rstrip('/'), filename=filename)

    fig.savefig(path, dpi=240, transparent=False)
    os.chmod(path, 0o644)

    return filename, path


# Util function to construct comma-separated strings in the form of:
# "foo" or "foo and bar" or "foo, bar, and baz" or "foo, bar, baz, and (n) other topics"
def comma_separate(items: List[str]) -> str:
    if len(items) == 1:
        return f'"{items[0]}"'
    elif len(items) <= 3:
        return ', '.join(map(lambda s: f'"{s}"', items[:-1])) + f'{"," if len(items) == 3 else ""} and "{items[-1]}"'
    else:
        return ', '.join(map(lambda s: f'"{s}"', items[:3])) + f', and {len(items) - 3} other topics'


"""
Method to convert a string to an integer that's a bit more complex than the default int converter
"""


def convert_int(argument: str):
    if argument.casefold().startswith('0x'):
        # Hexadecimal
        return int(argument, base=0)
    elif argument.casefold().startswith('0b'):
        # Binary
        return int(argument, base=0)
    else:
        # Check if it's something like sys.maxint/maxint, etc?
        return int(argument, base=10)


class Karma:

    def __init__(self, bot):
        self.bot = bot

    @commands.group(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def karma(self, ctx: Context):
        if not ctx.invoked_subcommand:
            await ctx.send("Subcommand not found")

    # @karma.command(help='Admin only command to set the karma of a topic to a specific value')
    # @is_compsoc_exec()
    # async def set(self, ctx: Context, karma: clean_content, value: clean_content):
    #     # Make sure that there's a karma topic to change
    #     if not karma:
    #         raise BadArgument(message='The karma topic must not be blank.')
    #
    #     if not value:
    #         raise BadArgument(message='The value of karma must not be blank.')
    #
    #     # Strip any leading @s and get the item from the DB
    #     karma_stripped = karma.lstrip('@')
    #     karma_item = db_session.query(KarmaModel).filter(
    #         func.lower(KarmaModel.name) == func.lower(karma_stripped)).first()
    #
    #     # If the item doesn't exist then create it
    #     if not karma_item:
    #         # The item hasn't been karma'd
    #         result = f'"{karma_stripped}" hasn\'t been karma\'d yet. :cry:'
    #         await ctx.send(result)
    #
    #     new_score = convert_int(str(value))
    #
    #     # Get karma-ing user
    #     user = db_session.query(User).filter(User.user_uid == ctx.message.author.id).first()
    #
    #     # Get the last change (or none if there was none)
    #     last_change = db_session.query(KarmaChange).filter(KarmaChange.karma_id == karma_item.id).order_by(
    #         desc(KarmaChange.created_at)).first()
    #
    #     # Create the karma change and commit it
    #     karma_change = KarmaChange(karma_id=karma_item.id, user_id=user.id, message_id=ctx.message.id,
    #                                reasons=[f'Set by {user.username} to {new_score}'], score=new_score,
    #                                change=(new_score - last_change.score), created_at=datetime.utcnow())
    #     db_session.add(karma_change)
    #
    #     await ctx.send(str(karma_change))

    # @set.error
    # async def karma_generic_error(self, ctx: Context, error: CommandError):
    #     if isinstance(error, BadArgument):
    #         if 'IntConverter' in str(error):
    #             await ctx.send('The value to set that topic to must be an integer.')
    #         else:
    #             await ctx.send(error)

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

    @karma.command(help='Gives information about the specified karma topic', ignore_extra=True)
    @commands.cooldown(5, 60, BucketType.user)
    async def info(self, ctx: Context, karma: clean_content):
        await ctx.trigger_typing()
        t_start = current_milli_time()
        # Strip any leading @s and get the item from the DB
        karma_stripped = karma.lstrip('@')
        karma_item = db_session.query(KarmaModel).filter(
            func.lower(KarmaModel.name) == func.lower(karma_stripped)).first()

        # If the item doesn't exist then raise an error
        if not karma_item:
            raise KarmaError(message=f'"{karma_stripped}" hasn\'t been karma\'d yet. :cry:')

        # Get the changes and plot the graph
        filename, path = await plot_karma({karma_stripped: karma_item.changes})

        # Get the user with the most karma
        # I'd use a group_by sql statement here but it seems to not terminate
        all_changes = db_session.query(KarmaChange).filter(KarmaChange.karma_id == karma_item.id) \
            .order_by(KarmaChange.created_at.asc()).all()
        user_changes = defaultdict(list)
        for change in all_changes:
            user_changes[change.user].append(change)

        most_karma = max(user_changes.items(), key=lambda item: len(item[1]))

        # Calculate the approval rating of the karma
        approval = 100 * ((karma_item.pluses - karma_item.minuses) / (karma_item.pluses + karma_item.minuses))
        mins_per_karma = (all_changes[-1].local_time - all_changes[0].local_time).total_seconds() / (
                60 * len(all_changes))
        time_taken = (current_milli_time() - t_start) / 1000

        # Attach the file as an image for dev purposes
        if CONFIG['DEBUG']:
            # Attach the file as an image for dev purposes
            plot_image = open(path, mode='rb')
            plot = File(plot_image)
            await ctx.send(f'Here\'s the karma trend for "{karma_stripped}" over time', file=plot)
        else:
            # Construct the embed
            generated_at = datetime.strftime(utc.localize(datetime.utcnow()).astimezone(timezone('Europe/London')),
                                             '%H:%M %d %b %Y')
            embed_colour = Color.from_rgb(61, 83, 255)
            embed_title = f'Statistics for "{karma_stripped}"'
            embed_description = f'"{karma_stripped}" has been karma\'d {len(all_changes)} {pluralise(all_changes, "time")} by {len(user_changes.keys())} {pluralise(user_changes.keys(), "user")}.'

            embed = Embed(title=embed_title, description=embed_description, color=embed_colour)
            embed.add_field(name='Most karma\'d',
                            value=f'"{karma_stripped}" has been karma\'d the most by <@{most_karma[0].user_uid}> with a total of {len(most_karma[1])} {pluralise(most_karma[1], "change")}.')
            embed.add_field(name='Approval rating',
                            value=f'The approval rating of "{karma_stripped}" is {approval:.1f}% ({karma_item.pluses} positive to {karma_item.minuses} negative karma and {karma_item.neutrals} neutral karma).')
            embed.add_field(name='Karma timeline',
                            value=f'"{karma_stripped}" was first karma\'d on {datetime.strftime(all_changes[0].local_time, "%d %b %Y at %H:%M")} and has been karma\'d approximately every {mins_per_karma:.1f} minutes.')
            embed.set_footer(text=f'Statistics generated at {generated_at} in {time_taken:.3f} seconds.')
            embed.set_image(url='{host}/{filename}'.format(host=CONFIG['FIG_HOST_URL'], filename=filename))

            display_name = get_name_string(ctx.message)
            await ctx.send(f'Here you go, {display_name}! :page_facing_up:', embed=embed)

    @info.error
    async def info_error(self, ctx: Context, error: CommandError):
        if isinstance(error, MissingRequiredArgument):
            await ctx.send('You need to give a karma topic to get information about. :frowning:')
        elif isinstance(error, KarmaError):
            await ctx.send(error.message)

    @karma.command(help='Plots the karma change over time of the given karma topic(s)')
    @commands.cooldown(5, 60, BucketType.user)
    async def plot(self, ctx: Context, *args: clean_content):
        await ctx.trigger_typing()
        t_start = current_milli_time()

        # If there are no arguments
        if not args:
            raise KarmaError(message='I can\'t')

        karma_dict = dict()
        failed = []

        # Iterate over the karma item(s)
        for karma in args:
            karma_stripped = karma.lstrip('@')
            karma_item = db_session.query(KarmaModel).filter(
                func.lower(KarmaModel.name) == func.lower(karma_stripped)).first()

            # Bucket the karma item(s) based on existence in the database
            if not karma_item:
                failed.append((karma_stripped, 'hasn\'t been karma\'d'))
                continue

            # Check if the topic has been karma'd >=10 times
            if len(karma_item.changes) < 5:
                failed.append((karma_stripped,
                               f'must have been karma\'d at least 5 times before a plot can be made (currently karma\'d {len(karma_item.changes)} {pluralise(karma_item.changes, "time")})'))
                continue

            # Add the karma changes to the dict
            karma_dict[karma_stripped] = karma_item.changes

        # Plot the graph and save it to a png
        filename, path = await plot_karma(karma_dict)
        t_end = current_milli_time()

        if CONFIG['DEBUG']:
            # Attach the file as an image for dev purposes
            plot_image = open(path, mode='rb')
            plot = File(plot_image)
            await ctx.send(f'Here\'s the karma trend for "{karma}" over time', file=plot)
        else:
            # Construct the embed
            generated_at = datetime.strftime(utc.localize(datetime.utcnow()).astimezone(timezone('Europe/London')),
                                             '%H:%M %d %b %Y')
            time_taken = (t_end - t_start) / 1000
            total_changes = reduce(lambda count, size: count + size, map(lambda t: len(t[1]), karma_dict.items()), 0)
            # Construct the embed strings
            if karma_dict.keys():
                embed_colour = Color.from_rgb(61, 83, 255)
                embed_description = f'Tracked {len(karma_dict.keys())} {pluralise(karma_dict.keys(), "topic")} with a total of {total_changes} changes'
                embed_title = f'Karma trend over time for {comma_separate(list(karma_dict.keys()))}' if len(
                    karma_dict.keys()) == 1 \
                    else f'Karma trends over time for {comma_separate(list(karma_dict.keys()))}'
            else:
                embed_colour = Color.from_rgb(255, 23, 68)
                embed_description = f'The following {pluralise(failed, "problem")} occurred whilst plotting:'
                embed_title = f'Could not plot karma for {comma_separate(list(map(lambda i: i[0], failed)))}'
            embed = Embed(color=embed_colour, title=embed_title, description=embed_description)
            # If there were any errors then add them
            for karma, reason in failed:
                embed.add_field(name=f'Failed to plot "{karma}"', value=f' • {reason}')

            # There was something plotted so attach the graph
            if karma_dict.keys():
                embed.set_footer(text=f'Graph generated at {generated_at} in {time_taken:.3f} seconds')
                embed.set_image(url='{host}/{filename}'.format(host=CONFIG['FIG_HOST_URL'], filename=filename))

            display_name = get_name_string(ctx.message)
            await ctx.send(f'Here you go, {display_name}! :chart_with_upwards_trend:', embed=embed)

    @plot.error
    async def plot_error_handler(self, ctx: Context, error: KarmaError):
        await ctx.send(error.message)

    @karma.command(help='Lists the reasons (if any) for the specific karma', ignore_extra=True)
    async def reasons(self, ctx: Context, karma: clean_content):
        karma_stripped = karma.lstrip('@')

        # Get the karma from the database
        karma_item = db_session.query(KarmaModel).filter(
            func.lower(KarmaModel.name) == func.lower(karma_stripped)).first()

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
