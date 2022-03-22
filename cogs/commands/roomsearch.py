from io import BytesIO

import discord
import requests
from discord.ext import commands
from discord.ext.commands import Bot, Context

LONG_HELP_TEXT = """
Finds a room on the various Warwick systems
"""

SHORT_HELP_TEXT = """Warwick Room Search"""


class RoomSearch(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def room(self, ctx: Context, name: str):
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

        desc = f"Building: **{room['building']}** {room['floor']}\n"
        desc += f"**[Campus Map](https://campus.warwick.ac.uk/?cmsid={room['id']})**\n"
        desc += f"**[Room Info (if centrally timetabled)](https://warwick.ac.uk/services/its/servicessupport/av/lecturerooms/roominformation/{room['name'].replace('.', '')})**\n"
        desc += f"`Timetable coming soon?`\n"
        desc += f"[Warwick Search](https://search.warwick.ac.uk/?q={name}) Room Capacity: {room['roomCapacity']}\n"

        embed = discord.Embed(title=f"Room Search: {room['name']}", description=desc)

        img = discord.File(
            self.req_img(
                "https://search.warwick.ac.uk/api/map-thumbnail/" + str(room["w2gid"])
            ),
            filename="map.png",
        )
        embed.set_image(url="attachment://map.png")

        await ctx.reply(embed=embed, file=img)

    async def choose_room(self, ctx, rooms):
        full_emojis = ["1️⃣", "2⃣", "3⃣", "4⃣", "5⃣", "6⃣", "7⃣", "8⃣", "9⃣", "🔟"]
        emojis = full_emojis[: len(rooms)]
        header = "Multiple rooms exist with that name, which do you want:"
        rooms_text = "".join(
            f"\n\t{e} {r['name']} in **{r['building']}** {r['floor']}"
            for r, e in zip(rooms, emojis)
        )
        conf_message = await ctx.send(header + rooms_text)
        for e in emojis:
            await conf_message.add_reaction(e)

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

        ind = emojis.index(str(react_emoji))
        return rooms[ind]

    def get_room_infos(self, room):
        # Swap with campus map autocomplete for more reliability? but that need auth
        map_req = self.req_or_none("https://search.warwick.ac.uk/api/maps?q=" + room)
        if map_req is None or map_req["total"] == 0:
            return []
        return map_req["results"]

    def req_or_none(self, url):
        r = requests.get(url)
        if not r.ok:
            return None
        return r.json()

    def req_img(self, url):
        r = requests.get(url)
        bytes = BytesIO(r.content)
        return bytes


def setup(bot: Bot):
    bot.add_cog(RoomSearch(bot))
