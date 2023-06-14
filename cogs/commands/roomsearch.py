import asyncio
import json
import logging
from datetime import date, datetime, time, timedelta
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import discord
from discord.ext import commands
from discord.ext.commands import Bot, Context

import utils

# from cogs.commands.karma_admin import MiniKarmaMode, get_mini_karma

room_resource_root = Path() / "resources" / "rooms"
# Same for all requests from campus map, so hardcode here as well
map_api_token = "Token 626629bcd5c05c5269b48ccb"

img_cache_dir = room_resource_root / "images"
img_cache_dir.mkdir(parents=True, exist_ok=True)
img_cache_paths = set(map(str, img_cache_dir.glob("*.png")))
logging.info(f"Currently cached rooms {img_cache_paths}")


def read_json_file(filename):
    # Read room name to timetable url mapping
    with open(str(filename)) as f:
        return json.load(f)


class RoomSearch(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.full_emojis = ("1️⃣", "2⃣", "3⃣", "4⃣", "5⃣", "6⃣", "7⃣", "8⃣", "9⃣", "🔟")

        root = room_resource_root
        self.central_rooms = read_json_file(root / "central-room-data.json")
        self.custom_room_names = read_json_file(root / "custom-room-mapname.json")
        self.timetable_room_mapping = read_json_file(root / "room_to_surl.json")
        self.last_week_check = None
        self.year = None
        self.week = None
        self.wb = None
        self.next_wb = None

    @commands.hybrid_command()
    async def roompr(self, ctx: Context):
        await ctx.reply(
            "This bot uses the Campus Map's API (<https://campus.warwick.ac.uk/>)."
            "If a name is wrong/missing on there, either ask exec to add it, "
            "or create a PR to add an alias in `resources/rooms/room-mapname.json`"
        )

    @commands.hybrid_command()
    async def room(self, ctx: Context, *, name: str):
        """Warwick Room Search

        Finds a room on the various Warwick systems.
        """
        # mini = get_mini_karma(ctx.channel.id) == MiniKarmaMode.Mini

        # Look up name in custom room dict
        clean_name = self.clean_name(name)
        if new := self.custom_room_names.get(clean_name):
            name = new
            clean_name = self.clean_name(name)
        rooms = await self.get_room_infos(name)
        if not rooms:
            return await ctx.reply(
                "Room does not exist. Try a more general search, "
                "or suggest a room alias (more info with `!roompr`)"
            )
        print(rooms)
        if len(rooms) > 1:
            # If exact match, use that
            for r in rooms:
                if (
                    self.clean_name(r.get("name")) == clean_name
                    or self.clean_name(r.get("displayName")) == clean_name
                ):
                    room = r
                    break
            else:  # Otherwise give user choice
                room = await self.choose_room(ctx, rooms)
            if room is None:
                return
        else:
            room = rooms[0]  # Only one in rooms

        print(room)
        ext_ref = room.get("extRef") or {}
        # if not mini:
        # Room info
        embed = discord.Embed(
            title=f"Room Search: {room.get('displayName')}",
            description=f"Building: **{room.get('parent').get('displayName')}** {ext_ref.get('floor')}",
        )
        # Campus Map
        content = f"**[{room.get('displayName')}]({self.get_map_url(room)})**"
        embed.add_field(
            name="Campus Map:",
            value=content,
            inline=True,
        )

        # Room info (for centrally timetabled rooms)
        if url := self.get_info_url(room):
            embed.add_field(
                name="Room Info:",
                value=f"**[{room.get('name')}]({url})**",
                inline=True,
            )

        # Timetable
        if urls := await self.get_tt_urls(room):
            in_term, _, _ = self.get_next_term_weeks()
            content = (
                f"**[This Week (wb {self.wb})]({urls[0]})**\n"
                + f"[Next Week (wb {self.next_wb})]({urls[1]})\n"
                + f"[{'This' if in_term else 'Next'} Term]({urls[2]})"
            )

            embed.add_field(
                name="Timetable:",
                value=content,
                inline=True,
            )
        # else:  # If mini
        #     desc = f"Building: **{ext_ref.get('building')} {ext_ref.get('floor')}**\n"
        #     # Timetable
        #     if urls := await self.get_tt_urls(room):
        #         in_term, _, _ = self.get_next_term_weeks()
        #         desc += (
        #             f"Timetable:⠀**[This Week]({urls[0]})**⠀"
        #             + f"[Next Week]({urls[1]})⠀"
        #             + f"[{'This' if in_term else 'Next'} Term]({urls[2]})\n"
        #         )

        #     # Campus Map
        #     desc += f"**[Campus Map]({self.get_map_url(room)})**"
        #     # Room info (for centrally timetabled rooms)
        #     if url := self.get_info_url(room):
        #         desc += f"⠀**[Room Info]({url})**"

        #     embed = discord.Embed(
        #         title=f"Room Search: {room.get('displayName')}",
        #         description=desc,
        #     )

        # img = await self.get_img(ctx, room.get("w2gid"))
        # if not mini:
        #     embed.set_image(url="attachment://map.png")
        #     embed.set_footer(
        #         text="Missing a room? Add it with a PR or ask exec to add an alias. !roompr for more"
        #     )
        # else:
        #     embed.set_thumbnail(url="attachment://map.png")
        msg = await ctx.reply(embed=embed)  # , file=img)

    def get_map_url(self, room):
        """Constructs url for campus map for room"""
        return f"https://campus.warwick.ac.uk/?slid={room.get('extRef').get('id')}"

    def get_info_url(self, room):
        """Constructs url for ITS info on room"""
        if url := self.is_central(room.get("name")):
            return f"https://warwick.ac.uk/services/its/servicessupport/av/lecturerooms/roominformation/{url}"
        return None

    async def get_tt_urls(self, room):
        """Constructs urls for timetable for room"""
        tt_room_id = self.timetable_room_mapping.get(room.get("name"))
        if tt_room_id is None:
            return None
        await self.get_week()
        if self.year is None:
            return None
        in_term, _, _ = self.get_next_term_weeks()
        return (
            self.get_this_week_url(room, tt_room_id),
            self.get_next_week_url(room, tt_room_id),
            self.get_term_url(room, tt_room_id),
        )

    def get_this_week_url(self, room, tt_room_id):
        """Constructs url for current week timetable for room"""
        this_year = self.year.replace("/", "")
        return f"https://timetablingmanagement.warwick.ac.uk/SWS{this_year}/roomtimetable.asp?id={quote(tt_room_id)}&week={self.week}"

    def get_next_week_url(self, room, tt_room_id):
        """Constructs url for next week timetable for room"""
        this_year = self.year.replace("/", "")
        if self.week < 52:  # Deal with wrap around on welcome week
            next_week_year = this_year
            next_week = self.week + 1
        else:
            year_int = int(this_year[:2]) + 1
            next_week_year = f"{year_int}{year_int+1}"
            next_week = 1
        return f"https://timetablingmanagement.warwick.ac.uk/SWS{next_week_year}/roomtimetable.asp?id={quote(tt_room_id)}&week={next_week}"

    def get_term_url(self, room, tt_room_id):
        """Constructs url for current/next term timetable for room"""
        in_term, term_wks, term_yr = self.get_next_term_weeks()
        return f"https://timetablingmanagement.warwick.ac.uk/SWS{term_yr}/roomtimetable.asp?id={quote(tt_room_id)}&week={term_wks}"

    def get_next_term_weeks(self):
        """Gets week range for current/next term timetable for room"""
        this_year = self.year.replace("/", "")
        term_yr = this_year
        # If in holiday, give dates of next term, otherwise current
        if 1 <= self.week <= 10:  # T1
            in_term, term_wks = True, "1-10"
        elif 11 <= self.week <= 14:  # Xmas
            in_term, term_wks = False, "15-24"
        elif 15 <= self.week <= 24:  # T2
            in_term, term_wks = True, "15-24"
        elif 25 <= self.week <= 29:  # Easter
            in_term, term_wks = False, "30-39"
        elif 30 <= self.week <= 39:  # T3
            in_term, term_wks = True, "30-39"
        else:  # Summer
            in_term, term_wks = False, "1-10"
            year_int = int(this_year[:2]) + 1
            term_yr = f"{year_int}{year_int+1}"
        return in_term, term_wks, term_yr

    # async def get_img(self, ctx, w2gid):
    #     """Fetch location preview image for room, but cache to disk"""
    #     # The fetch slows command down quite a lot, but Discord can't take images without extensions
    #     # Cache file on disk if not fetched before
    #     fp = img_cache_dir / f"{w2gid}.png"
    #     if str(fp) not in img_cache_paths:
    #         logging.info(f"Caching img for room {w2gid}")
    #         img = await utils.get_from_url(
    #             f"https://search.warwick.ac.uk/api/map-thumbnail/{w2gid}"
    #         )

    #         with open(fp, "wb") as f:
    #             f.write(img)
    #         img_cache_paths.add(str(fp))
    #         return discord.File(BytesIO(img), filename="map.png")
    #     else:
    #         with open(fp, "rb") as f:
    #             return discord.File(f, filename="map.png")

    async def choose_room(self, ctx, rooms):
        """Confirms room choice, esp. important with autocomplete api"""
        # Create and send message
        emojis = self.full_emojis[: len(rooms)]
        header = "Multiple rooms exist with that name. Which do you want?:"
        rooms_text = "".join(
            f"\n\t{e} {r.get('name')} in **{r.get('parent').get('displayName')}** {r.get('extRef').get('floor')}"
            for r, e in zip(rooms, emojis)
        )
        conf_message = await ctx.send(header + rooms_text)

        # Add reacts to choice msg
        async def add_reacts():
            try:
                for e in emojis:
                    await conf_message.add_reaction(e)
            except discord.NotFound:
                pass

        # Check for user react on msg
        async def check_reacts():
            try:
                check = (
                    lambda r, u: r.message.id == conf_message.id
                    and u == ctx.message.author
                    and str(r.emoji) in emojis
                )
                react_emoji, _ = await ctx.bot.wait_for(
                    "reaction_add", check=check, timeout=30
                )
                return react_emoji
            except TimeoutError:
                return None
            finally:
                await conf_message.delete()

        # Add and check in parallel, so don't miss quick react
        _, react_emoji = await asyncio.gather(add_reacts(), check_reacts())

        # Get choice
        ind = emojis.index(str(react_emoji))
        return rooms[ind]

    async def get_room_infos(self, room):
        # Check Map Autocomplete API
        map_req = await utils.get_json_from_url(
            f"https://hub.smartne.com/api/store/projects/warwick/live/locations/search/{room}?limit=10&fields=name,displayName,parent,floor,extRef",
            {"Authorization": map_api_token},
        )
        if map_req is None:
            return []

        return self.remove_duplicate_rooms(map_req)

    def remove_duplicate_rooms(self, rooms):
        # remove = [r for r in rooms if r.get("w2gid") is None]
        # for room in remove:
        #     rooms.remove(room)

        # Map has duplicate entries for MSB for some reason
        # rooms = self.remove_duplicate_building(
        #     rooms, "Mathematical Sciences", "Mathematical Sciences Building"
        # )
        return rooms

    # def remove_duplicate_building(self, rooms, orig, copy):
    #     orig_rooms = [r for r in rooms if r.get("building") == orig]
    #     fake_rooms = [r for r in rooms if r.get("building") == copy]
    #     for orig_room in orig_rooms:
    #         fake_room = next(
    #             (r for r in fake_rooms if orig_room.get("value") == r.get("value")),
    #             None,
    #         )
    #         if fake_room:
    #             rooms.remove(fake_room)
    #     return rooms

    async def get_week(self):
        # Definitely don't need to check each request
        # Only check if last request was before today
        today = datetime.combine(date.today(), time.min)

        if self.last_week_check is None or self.last_week_check < today:
            self.last_week_check = datetime.now()
            weeks_json = await utils.get_json_from_url(
                "https://tabula.warwick.ac.uk/api/v1/termdates/weeks"
            )

            # TODO Could binary search here as sorted
            for week in weeks_json["weeks"]:
                start = datetime.strptime(week.get("start"), "%Y-%m-%d").date()
                end = datetime.strptime(week.get("end"), "%Y-%m-%d").date()
                current = (datetime.now() + timedelta(days=1)).date()
                if start < current <= end:
                    self.year = week.get("academicYear")
                    self.week = week.get("weekNumber")
                    self.wb = start.strftime("%d %b")
                    self.next_wb = (start + timedelta(weeks=1)).strftime("%d %b")
                    return self.year, self.week
                if current < start:  # As sorted, no matches
                    break
            return None, None
        return self.year, self.week

    def is_central(self, room_name):
        # Checks if room is centrally timetabled from central-room-data.json (from Tabula)
        for building in self.central_rooms:
            for r in building.get("rooms"):
                if r.get("name") == room_name:
                    return r.get("url")
        return None

    def clean_name(self, name):
        return name.lower().strip().replace(".", "")


async def setup(bot: Bot):
    await bot.add_cog(RoomSearch(bot))
