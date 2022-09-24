from datetime import datetime
import io

import requests
import discord
from discord.ext import commands
from discord.ext.commands import Bot, Context
from icalendar import Calendar, Event
from models.event_sync import EventLink
from models import db_session
import datetime
from sqlalchemy.dialects.postgresql import insert
from utils.utils import wait_react

LONG_HELP_TEXT = """
Sync events to our website uwcs.co.uk/events."""

SHORT_HELP_TEXT = """Sync events"""

ICAL_URL = "https://uwcs.co.uk/signups/feed.ics"

class Sync(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    @wait_react
    async def event(self, ctx: Context):
        # Fetch and parse ical from website
        r = requests.get(ICAL_URL)
        c = io.BytesIO(r.content)
        cal = Calendar.from_ical(c.getvalue())
        db_links = db_session.query(EventLink).all()
        links = {e.uid: e for e in db_links}

        dc_events = await ctx.guild.fetch_scheduled_events()
        dc_events = {e.id: e for e in dc_events}
        # Add events
        for ev in cal.walk():
            if ev.name != "VEVENT":
                continue

            event_args = self.ical_event_to_dc_args(ev)

            # Check for existing 
            uid = ev.get("uid")
            link = links.get(uid)

            # Attempt to find existing event
            event = None
            if link:
                event = dc_events.get(link.discord_event)
            
            # If doesn't exist create a new event
            if not event:
                # Create new event
                event = await ctx.guild.create_scheduled_event(**event_args)
                await ctx.send(f"Created event **{ev.get('summary')}** at event {event.url}")
            else:
                # Don't edit if no change
                if self.check_event_equiv(event_args, event):
                    # Updat existing event
                    await event.edit(**event_args)
                    await ctx.send(f"Updated event **{ev.get('summary')}** at event {event.url}")
                else:
                    # Don't change event
                    await ctx.send(f"No change for event **{ev.get('summary')}**")

            self.update_db_link(uid, event.id, link)

    
    @staticmethod
    def ical_event_to_dc_args(ev):
    # Construct args for discord event
        desc = f"{ev.get('description')}\n\nSee more at {ev.get('url')}"
        return {
            "name": str(ev.get("summary")),
            "description": desc,
            "start_time": ev.decoded("dtstart"),
            "end_time": ev.decoded("dtend"),
            "entity_type": discord.EntityType.external,
            "location": str(ev.get("location")),
        }

    @staticmethod
    def check_event_equiv(event_args, event):
        old_args = {"name": event.name, "description": event.description, "start_time": event.start_time, "end_time": event.end_time, "entity_type": event.entity_type, "location": event.location}
        return event_args != old_args

    @staticmethod
    def update_db_link(uid, event_id, link):
        # Update database record
        now = datetime.datetime.now()
        if not link:
            link = EventLink(uid=uid, discord_event=event_id, last_modified=now)
            db_session.add(link)
        else:
            link.discord_event = event_id
        link.last_modified = now
            
        db_session.commit()

async def setup(bot: Bot):
    await bot.add_cog(Sync(bot))
