import datetime
import io
import re
from html import unescape
from pprint import pprint

import discord
from discord.ext import commands
from discord.ext.commands import Bot, Context
from icalendar import Calendar
from pytz import timezone

from models import db_session
from models.event_sync import EventLink
from utils.utils import get_json_from_url, is_compsoc_exec_in_guild

LONG_HELP_TEXT = """
Sync events to our website uwcs.co.uk/events."""

SHORT_HELP_TEXT = """Sync events"""

ICAL_URL = "https://oengus.io/api/v2/marathons/wasd2025/schedules/for-slug/wasd2025"

def duration(duration_str):
    match = re.match(
        r'P((?P<years>\d+)Y)?((?P<months>\d+)M)?((?P<weeks>\d+)W)?((?P<days>\d+)D)?(T((?P<hours>\d+)H)?((?P<minutes>\d+)M)?((?P<seconds>\d+)S)?)?',
        duration_str
    ).groupdict()
    return int(match['years'] or 0)*365*24*3600 + \
        int(match['months'] or 0)*30*24*3600 + \
        int(match['weeks'] or 0)*7*24*3600 + \
        int(match['days'] or 0)*24*3600 + \
        int(match['hours'] or 0)*3600 + \
        int(match['minutes'] or 0)*60 + \
        int(match['seconds'] or 0)


class Sync(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    @commands.check(is_compsoc_exec_in_guild)
    async def event(self, ctx: Context, days: int = 7, logging: bool = False):
        now = datetime.datetime.now(timezone("Europe/London"))
        # datetime's main module also being called datetime is annoying
        before = now + datetime.timedelta(days=days)

        await ctx.send(f"Syncing events from {now} to {before}")

        # Fetch and parse ical from website
        cal = await get_json_from_url("https://oengus.io/api/v2/marathons/wasd2025/schedules/for-slug/wasd2025")
        if logging: await ctx.send("Got JSON")
        
        db_links = db_session.query(EventLink).all()
        links = {e.uid: e for e in db_links}

        dc_events = await ctx.guild.fetch_scheduled_events()
        dc_events = {e.id: e for e in dc_events}

        pprint(links)

        pprint(dc_events)

        # Add events
        for ev in cal["lines"]:
            if not ev.get("runners"): continue

            t = datetime.datetime.strptime(ev["date"], "%Y-%m-%dT%H:%M:%SZ")
            t = t.astimezone(timezone("UTC"))
            print(ev["game"], t, before, now)
            if t < now:
                await self.log_event(ctx, ev, t, logging, "in the past")
                continue
            if t > before:
                await self.log_event(ctx, ev, t, logging, "outside time frme")
                continue
            await self.update_event(ctx, ev, links, dc_events, logging)
        await ctx.send("Done :)")

    async def log_event(self, ctx, ev, t, logging, reason):
        if logging:
            await ctx.send(f"Skipping event  at time {t} as it is {reason}")

    async def update_event(self, ctx, ev, links, dc_events, logging):
        """Check discord events for match, update if existing, otherwise create it"""
        event_args = await self.ical_event_to_dc_args(ev, ctx)

        # Check for existing
        uid = str(ev["id"])
        link = links.get(uid)

        # Attempt to find existing event
        event = None
        if link:
            event = dc_events.get(link.discord_event)

        # If doesn't exist create a new event
        if not event:
            # Create new event
            event = await ctx.guild.create_scheduled_event(**event_args)
            if logging: await ctx.send(
                f"Created event **{ev.get('game')}** at event {event.url}"
            )
        else:
            # Don't edit if no change
            if self.check_event_equiv(event_args, event):
                # Updat existing event
                await event.edit(**event_args)
                if logging: await ctx.send(
                    f"Updated event **{ev.get('game')}** at event {event.url}"
                )
            else:
                # Don't change event
                if logging: await ctx.send(f"No change for event **{ev.get('game')}**")

        self.update_db_link(uid, event.id, link)

    async def find_person(self, person, ctx):
        basic_name = person["runnerName"]

        if not basic_name: return None

        custom = {
            "IronScorpion": "iron_scorpion",
            "OblivionWing": "oblivionwing."
        }

        username = custom.get(basic_name)

        if not username:
            profile = person.get("profile", {})
            for conn in profile.get("connections", []):
                if conn["platform"] == "DISCORD":
                        username = conn["username"]
                        if "#" in username: username = username.split("#")[0]
        if not username: username = basic_name

        try:
            user = await commands.UserConverter().convert(ctx, username)
            return user.mention
        except:
            print(username, username.lower())
            try:
                user = await commands.UserConverter().convert(ctx, username.lower())
                return user.mention
            except: pass
        return basic_name


    async def ical_event_to_dc_args(self, ev, ctx):
        """Construct args for discord event from the ical event"""
        # desc = ev["category"] + "\nWith " + (" vs. ".join(map(lambda t: " & ".join(map(lambda p: p["name"], t["players"])), ev.get("runners", []))))
        usernames = []
        for player in ev["runners"] or []:
            name = await self.find_person(player, ctx)
            usernames.append(name)
        
        players = " vs ".join(usernames)
        start = datetime.datetime.strptime(ev["date"], "%Y-%m-%dT%H:%M:%SZ")
        start = start.astimezone(timezone("UTC"))
        dur = duration(ev["estimate"])
        end = start + datetime.timedelta(seconds=dur if dur > 1 else 1)
        return {
            "name": ev["game"] + ("" if not ev.get("type") == "RACE" else " - Race"),
            "description": ev["category"] + ("\nwith " if len(usernames) <= 1 else "\n") + players,
            "start_time": start,
            "end_time": end,
            "entity_type": discord.EntityType.external,
            "location": "Esports Centre, University of Warwick",
        }

    @staticmethod
    def check_event_equiv(event_args, event):
        """
        Checks if there has been a change to the event.
        Slight faff since we don't want to compare all fields of the discord event or the ical event
        """
        old_args = {
            "name": event.name,
            "description": event.description,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "entity_type": event.entity_type,
            "location": event.location,
        }
        return event_args != old_args

    @staticmethod
    def update_db_link(uid, event_id, link):
        """Update database record. If new, create, otherwise update"""
        now = datetime.datetime.now(timezone("Europe/London"))
        if not link:
            link = EventLink(uid=uid, discord_event=event_id, last_modified=now)
            db_session.add(link)
        else:
            link.discord_event = event_id
        link.last_modified = now

        db_session.commit()


async def setup(bot: Bot):
    await bot.add_cog(Sync(bot))
