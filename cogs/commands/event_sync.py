from datetime import datetime, timedelta

import discord
from discord.ext import commands
from discord.ext.commands import Bot, Context
from pytz import timezone

from models import db_session
from models.event_sync import EventLink
from utils.utils import get_json_from_url, is_compsoc_exec_in_guild

LONG_HELP_TEXT = """
Sync events to our website uwcs.co.uk/events."""

SHORT_HELP_TEXT = """Sync events"""

ENDPOINT = "https://events.uwcs.co.uk/api/events/days/"


class Sync(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    @commands.check(is_compsoc_exec_in_guild)
    async def event(self, ctx: Context, days: int = 7, logging: bool = False):
        now = datetime.now(timezone("Europe/London"))
        before = now + timedelta(days=days)

        await ctx.send(f"Syncing events from {now} to {before}")

        # get events from api
        events = await get_json_from_url(ENDPOINT + f"?days={days}")

        await ctx.send(f"Found {len(events)} event(s)")

        # set up link to db
        db_links = db_session.query(EventLink).all()
        links = {e.uid: e for e in db_links}

        # get existing events from discord
        dc_events = await ctx.guild.fetch_scheduled_events()
        dc_events = {e.id: e for e in dc_events}

        if not events:
            await ctx.send("No events found :(")
            return

        # Add events
        for ev in events:
            await self.update_event(ctx, ev, links, dc_events)

        await ctx.send("Done :)")

    async def update_event(self, ctx, ev, links, dc_events):
        """Check discord events for match, update if existing, otherwise create it"""
        event_args = self.api_event_to_dc_args(ev)

        # Check for existing
        uid = ev.get("url")
        link = links.get(uid)

        # Attempt to find existing event
        event = None
        if link:
            event = dc_events.get(link.discord_event)

        # If doesn't exist create a new event
        if not event:
            # Create new event
            event = await ctx.guild.create_scheduled_event(**event_args)
            await ctx.send(f"Created event **{ev.get('name')}** at event {event.url}")
        else:
            # Don't edit if no change
            if self.check_event_equiv(event_args, event):
                # Updat existing event
                await event.edit(**event_args)
                await ctx.send(
                    f"Updated event **{ev.get('summary')}** at event {event.url}"
                )
            else:
                # Don't change event
                await ctx.send(f"No change for event **{ev.get('summary')}**")

        self.update_db_link(uid, event.id, link)

    @staticmethod
    def api_event_to_dc_args(ev):
        """Construct args for discord event from the api event"""
        description = (
            (ev.get("description")[:500] + "...")
            if len(ev.get("description")) > 500
            else ev.get("description")
        )
        description += f"\n\nSee more at {ev.get('url')}"
        return {
            "name": ev.get("name"),
            "description": description,
            "start_time": datetime.strptime(
                ev.get("start_time"), "%Y-%m-%dT%H:%M"
            ).replace(tzinfo=timezone("Europe/London")),
            "end_time": datetime.strptime(ev.get("end_time"), "%Y-%m-%dT%H:%M").replace(
                tzinfo=timezone("Europe/London")
            ),
            "entity_type": discord.EntityType.external,
            "location": ev.get("location"),
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
        now = datetime.now(timezone("Europe/London"))
        if not link:
            link = EventLink(uid=uid, discord_event=event_id, last_modified=now)
            db_session.add(link)
        else:
            link.discord_event = event_id
        link.last_modified = now

        db_session.commit()


async def setup(bot: Bot):
    await bot.add_cog(Sync(bot))
