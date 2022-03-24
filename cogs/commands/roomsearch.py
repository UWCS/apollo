from io import BytesIO

import discord
import requests
from discord.ext import commands
from discord.ext.commands import Bot, Context


def req_or_none(url):
    r = requests.get(url)
    if not r.ok:
        return None
    return r.json()


def req_img(url):
    r = requests.get(url)
    bytes = BytesIO(r.content)
    return bytes


class RoomSearch(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.full_emojis = ("1️⃣", "2⃣", "3⃣", "4⃣", "5⃣", "6⃣", "7⃣", "8⃣", "9⃣", "🔟")

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

        desc = "\n".join([
            f"Building: **{room['building']}** {room['floor']}",
            f"**[Campus Map](https://campus.warwick.ac.uk/?cmsid={room['id']})**",
            f"**[Room Info (if centrally timetabled)](https://warwick.ac.uk/services/its/servicessupport/av/lecturerooms/roominformation/{room['name'].replace('.', '')})**",
            f"`Timetable coming soon?`",
            f"[Warwick Search](https://search.warwick.ac.uk/?q={name}) Room Capacity: {room['roomCapacity']}"
        ])

        embed = discord.Embed(title=f"Room Search: {room['name']}", description=desc)

        img = discord.File(
            req_img(f"https://search.warwick.ac.uk/api/map-thumbnail/{room['w2gid']}"),
            filename="map.png",
        )
        embed.set_image(url="attachment://map.png")

        await ctx.reply(embed=embed, file=img)

    async def choose_room(self, ctx, rooms):
        emojis = self.full_emojis[: len(rooms)]
        header = "Multiple rooms exist with that name. Which do you want?:"
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
        map_req = req_or_none(f"https://search.warwick.ac.uk/api/maps?q={room}")
        if map_req is None or map_req["total"] == 0:
            return []
        return map_req["results"]


def setup(bot: Bot):
    bot.add_cog(RoomSearch(bot))
