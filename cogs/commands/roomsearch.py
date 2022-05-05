import ast
from io import BytesIO

import discord
import requests
from discord.ext import commands
from discord.ext.commands import Bot, Context
from pathlib import Path
import json
from urllib.parse import quote
from datetime import datetime, date, time

room_resource_root = Path() / "resources" / "rooms"


def req_or_none(url, **kwargs):
    r = requests.get(url, **kwargs)
    if not r.ok:
        return None
    return r.json()


def req_img(url):
    r = requests.get(url)
    bytes = BytesIO(r.content)
    return bytes


def read_mapping(filename):
    # Read room name to timetable url mapping
    with open(str(filename)) as f:
        l = [l.split(" | ") for l in f.readlines()]
        return {x[0].strip(): x[1].strip() for x in l if len(x) > 1}


class RoomSearch(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.full_emojis = ("1️⃣", "2⃣", "3⃣", "4⃣", "5⃣", "6⃣", "7⃣", "8⃣", "9⃣", "🔟")

        raw = (room_resource_root / "central-room-data.json").read_text()
        self.central_rooms = json.loads(raw)
        self.custom_room_names = read_mapping(room_resource_root / "room-mapname.txt")
        self.timetable_room_mapping = read_mapping(
            room_resource_root / "room_to_surl.txt"
        )
        self.last_week_check = None
        self.year = None
        self.week = None

    @commands.command()
    async def room(self, ctx: Context, name: str):
        """Warwick Room Search

        Finds a room on the various Warwick systems.
        """
        rooms = self.get_room_infos(name)
        if not rooms:
            return await ctx.reply(
                "Room does not exist. Ensure you are giving the full name"
            )

        if len(rooms) > 1:
            room = await self.choose_room(ctx, rooms)
            if room is None:
                return
        else:
            room = rooms[0]  # Only one in rooms

            
        # Room info
        embed = discord.Embed(
            title=f"Room Search: {room.get('value')}",
            description=f"Building: **{room.get('building')} {room.get('floor')}**",
        )
        # Campus Map
        embed.add_field(
            name="Campus Map:",
            value=f"**[{room.get('value')}](https://campus.warwick.ac.uk/?cmsid={room.get('id')})**",
            inline=True,
        )
        # Room info (for centrally timetabled rooms)
        if url := self.is_central(room.get("value")):
            embed.add_field(
                name="Room Info:",
                value=f"**[{room.get('value')}](https://warwick.ac.uk/services/its/servicessupport/av/lecturerooms/roominformation/{url})**",
                inline=True,
            )
        # Timetable
        if tt_room_id := self.timetable_room_mapping.get(room.get("value")):
            self.get_week()
            embed.add_field(
                name="Timetable:",
                value=f"**[This Week](https://timetablingmanagement.warwick.ac.uk/SWS{self.year.replace('/', '')}/roomtimetable.asp?id={quote(tt_room_id)})**\n"
                f"[Next Week](https://timetablingmanagement.warwick.ac.uk/SWS{self.year.replace('/', '')}/roomtimetable.asp?id={quote(tt_room_id)}&week={self.week+1})\n",
                inline=True,
            )

        img = discord.File(
            req_img(
                f"https://search.warwick.ac.uk/api/map-thumbnail/{room.get('w2gid')}"
            ),
            filename="map.png",
        )
        embed.set_image(url="attachment://map.png")

        await ctx.reply(embed=embed, file=img)

    async def choose_room(self, ctx, rooms):
        # Confirms room choice, esp. important with autocomplete api
        # Create and send message
        emojis = self.full_emojis[: len(rooms)]
        header = "Multiple rooms exist with that name. Which do you want?:"
        rooms_text = "".join(
            f"\n\t{e} {r.get('value')} in **{r.get('building')}** {r.get('floor')}"
            for r, e in zip(rooms, emojis)
        )
        conf_message = await ctx.send(header + rooms_text)
        for e in emojis:
            await conf_message.add_reaction(e)

        # Wait for reaction
        try:
            check = (
                lambda r, u: r.message.id == conf_message.id
                and u == ctx.message.author
                and str(r.emoji) in emojis
            )
            react_emoji, _ = await ctx.bot.wait_for(
                "reaction_add", check=check, timeout=60
            )
        except TimeoutError:
            return None
        finally:
            await conf_message.delete()

        # Get choice
        ind = emojis.index(str(react_emoji))
        return rooms[ind]

    def get_room_infos(self, room):
        stripped = room.replace(".", "").replace(" ", "").lower()
        if new := self.custom_room_names.get(stripped):
            room = new
        # Check Map Autocomplete API
        map_req = req_or_none(
            f"https://campus-cms.warwick.ac.uk//api/v1/projects/1/autocomplete.json?term={room}",
            headers={"Authorization": "Token 3a08c5091e5e477faa6ea90e4ae3e6c3"},
        )
        if map_req is None:
            return []
        return self.remove_duplicate_rooms(map_req)

    def remove_duplicate_rooms(self, rooms):
        # Map has duplicate entries for MSB for some reason
        rooms = self.remove_duplicate_building(
            rooms, "Mathematical Sciences", "Mathematical Sciences Building"
        )
        return rooms

    def remove_duplicate_building(self, rooms, orig, copy):
        orig_rooms = [r for r in rooms if r.get("building") == orig]
        fake_rooms = [r for r in rooms if r.get("building") == copy]
        for orig_room in orig_rooms:
            fake_room = next(
                (r for r in fake_rooms if orig_room.get("value") == r.get("value")),
                None,
            )
            if fake_room:
                rooms.remove(fake_room)
        return rooms

    def get_week(self):
        # Definitely don't need to check each request
        # Only check if last request was before today
        today = datetime.combine(date.today(), time.min)

        if self.last_week_check is None or self.last_week_check < today:
            current = datetime.now()
            self.last_week_check = current
            print("Checking week")
            weeks_json = req_or_none(
                "https://tabula.warwick.ac.uk/api/v1/termdates/weeks"
            ).get("weeks")

            for week in weeks_json:
                start = datetime.strptime(week.get("start"), "%Y-%m-%d")
                end = datetime.strptime(week.get("end"), "%Y-%m-%d")
                if start < current < end:
                    self.year = week.get("academicYear")
                    self.week = week.get("weekNumber")
                    return self.year, self.week
            return None, None
        return self.year, self.week

    def is_central(self, room_name):
        # Checks if room is centrally timetabled from central-room-data.json (from Tabula)
        for building in self.central_rooms:
            for r in building.get("rooms"):
                if r.get("name") == room_name:
                    return r.get("url")
        return None


def setup(bot: Bot):
    bot.add_cog(RoomSearch(bot))
