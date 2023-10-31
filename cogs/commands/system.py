import logging
import platform
from datetime import datetime, timezone
from os import environ
from typing import Any

import aiohttp
import discord
from dateutil import parser
from discord.ext import commands
from discord.ext.commands import Bot, Context, check
from psycopg import OperationalError
from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError

from config import CONFIG
from models.models import db_session
from models.system import EventKind, SystemEvent
from utils import is_compsoc_exec_in_guild

APOLLO_ENDPOINT_URL = (
    "https://portainer.uwcs.co.uk/api/endpoints/2/docker/containers/apollo"
)


class System(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

        try:
            with open(".version", "r") as f:
                content = f.readlines()
                self.version_from_file = content[0].rstrip()
                self.build_timestamp_from_file = content[1].rstrip()
        except FileNotFoundError:
            logging.error("Could not load git revision from file")
            self.version_from_file = None
            self.build_timestamp_from_file = None

    @commands.hybrid_command()
    async def info(self, ctx: Context[Bot]):
        json = await self.get_docker_json()
        if json is None:
            return

        # these are likely to be outdated, so we don't use them.
        # version = json["Config"]["Labels"]["org.opencontainers.image.revision"]
        # built = json["Config"]["Labels"]["org.opencontainers.image.created"]

        version = self.version_from_file
        built = self.build_timestamp_from_file

        description: str = json["Config"]["Labels"][
            "org.opencontainers.image.description"
        ]

        py_version = platform.python_version()
        dpy_version = discord.__version__

        # the timestamp docker gives is in ISO 8601 format, but py3.10 does not fully support it
        timestamp: str = json["State"]["StartedAt"]
        started = parser.parse(timestamp)
        uptime = datetime.utcnow().astimezone(timezone.utc) - started.astimezone(
            timezone.utc
        )

        if version and built:
            reply = f"""Apollo, {description}\n
Built from Git revision {version[:8]} on {built[0:10]} {built[11:19]}
Python {py_version}, discord.py {dpy_version} 
Started {started.strftime("%d/%m/%y, %H:%M:%S")} (uptime {uptime})"""

        else:
            reply = f"""Apollo, {description}\n
Could not get build information
Python {py_version}, discord.py {dpy_version} 
Started {started} (uptime {uptime})"""
        await ctx.reply(reply)

    @commands.hybrid_command()
    async def version(self, ctx: Context[Bot]):
        """Get Apollo's version"""
        if self.version_from_file:
            await ctx.reply(f"`{self.version_from_file}`")
        else:
            await ctx.reply("Could not find version")

    @commands.hybrid_command()
    @check(is_compsoc_exec_in_guild)
    async def restart(self, ctx: Context[Bot]):
        headers = {"X-API-Key": f"{CONFIG.PORTAINER_API_KEY}"}
        db_comitted = True
        async with aiohttp.ClientSession(headers=headers) as session:
            event = SystemEvent(EventKind.RESTART, ctx.message.id, ctx.channel.id)
            try:
                db_session.add(event)
                db_session.commit()
            except (SQLAlchemyError, OperationalError):
                logging.error("Failed to add event to database")
                db_comitted = False
            await ctx.reply("Going down for reboot...")
            resp = await session.post(f"{APOLLO_ENDPOINT_URL}/restart")
            await self.process_fail(resp, ctx, db_comitted, "restart", event)

    @commands.hybrid_command()
    @check(is_compsoc_exec_in_guild)
    async def update(self, ctx: Context[Bot]):
        headers = {"X-API-Key": f"{CONFIG.PORTAINER_API_KEY}"}
        db_comitted = True
        async with aiohttp.ClientSession(headers=headers) as session:
            # Get ID to filter webhook list by
            info = await session.get(f"{APOLLO_ENDPOINT_URL}/json")
            id = (await info.json())["Id"]
            # Get Webhook token
            webhook_list_url = f'https://portainer.uwcs.co.uk/api/webhooks?filters={{"EndpointID":2,"ResourceID":"{id}"}}'
            webhook_list = await session.get(webhook_list_url)
            webhook_token = (await webhook_list.json())[0]["Token"]
            # Construct URL
            webhook_url = f"https://portainer.uwcs.co.uk/api/webhooks/{webhook_token}"
            logging.info(f"Recreate webhook url {webhook_url}")

            event = SystemEvent(EventKind.UPDATE, ctx.message.id, ctx.channel.id)
            try:
                db_session.add(event)
                db_session.commit()
            except (SQLAlchemyError, OperationalError):
                logging.error("Failed to add event to database")
                db_comitted = False
            await ctx.reply("Going down for update...")
            resp = await session.post(webhook_url)
            await self.process_fail(resp, ctx, db_comitted, "update", event)

    async def process_fail(
        self,
        resp: aiohttp.ClientResponse,
        ctx: Context[Bot],
        db_comitted: bool,
        action: str,
        event: SystemEvent,
    ):
        if not resp.ok:
            status = resp.status
            msg = (await resp.json())["message"]
            err_msg = f"Failed to {action}. {status} from Portainer API: {msg}"
            logging.error(err_msg)
            await ctx.reply(err_msg)
            if db_comitted:
                try:
                    # remove our event that just failed to happen
                    db_session.delete(event)
                    db_session.commit()
                except (SQLAlchemyError, OperationalError):
                    pass

    # TODO: same as above but re-create container
    # have to do it all through Docker API; fetch config, save it, pull image, start contaienr

    @commands.Cog.listener()
    async def on_ready(self):
        all_events = []
        # check for any unacknowledged events
        try:
            all_events = db_session.scalars(
                select(SystemEvent)
                .where(SystemEvent.acknowledged.is_(False))
                .order_by(desc(SystemEvent.time))
            ).all()
        except (SQLAlchemyError, OperationalError):
            logging.error("Failed to get system events from database")
            return
        if len(all_events) == 0:
            logging.info("No system events found in database")
            return
        latest, *old = all_events
        if len(old) != 0:
            logging.warn(
                "Old unacknowledged system events found, purging old and ackowledging recent"
            )
            for event in old:
                db_session.delete(event)

        channel = await self.bot.fetch_channel(latest.channel_id)
        if not isinstance(channel, (discord.TextChannel)):
            logging.error("message id invalid, cannot fetch message id")
            return

        try:
            message = await channel.fetch_message(latest.message_id)
            name = message.author.display_name
        except discord.NotFound:
            message = None
            name = "World"
        send = message.reply if message else channel.send
        await send(
            f"Hello {name}. Apollo, has {'started in' if latest.kind == EventKind.RESTART else 'updated to'} version {self.version_from_file}"
        )
        latest.acknowledged = True
        db_session.commit()

    @staticmethod
    async def get_docker_json() -> dict[Any, Any] | None:
        headers = {"X-API-Key": f"{CONFIG.PORTAINER_API_KEY}"}
        async with aiohttp.ClientSession(headers=headers) as session:
            resp = await session.get(f"{APOLLO_ENDPOINT_URL}/json")
            if not resp.ok:
                logging.error("Could not reach Portainer API")
                return None
            return await resp.json()


async def setup(bot: Bot):
    headers = {"X-API-Key": f"{CONFIG.PORTAINER_API_KEY}"}
    async with aiohttp.ClientSession(headers=headers) as session:
        resp = await session.get(f"{APOLLO_ENDPOINT_URL}/json")
    match (resp.ok, (environ.get("CONTAINER") is not None)):
        case (True, True):
            await bot.add_cog(System(bot))
        case (True, False):
            logging.error(
                "Can reach Portainer API but not running in container. Not loading system cog."
            )
        case (False, True):
            logging.error(
                "Running in container but can't reach Portainer API. Not loading system cog."
            )
        case _:
            logging.error("Not loading system cog.")
