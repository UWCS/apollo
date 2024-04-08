from datetime import timedelta

from discord.ext import commands
from discord.ext.commands import Bot, Context
from requests import get as get_request
from tabulate import tabulate

LONG_HELP_TEXT = """

Display F1 Statistics from current and past races

Session Names: 
    Practice 1, Practice 2, Practice 3, Qualifying, Race (Normal Format)
    Practice 1, Qualifying, Sprint Shootout, Sprint, Race (Sprint Format)

"""

SHORT_HELP_TEXT = """Make the bot repeat after you."""


base_url = "https://api.openf1.org/v1"


class F1(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def f1(
        self,
        ctx: Context,
        country: str = None,
        year: int = None,
        session_name: str = None,
    ):
        if country is None or year is None:
            raise Exception("Country or Year is Missing!")
        session_key = self.get_session(country, year, session_name)
        standings = await self.get_standings(session_key)
        standings = await self.standings_format(standings, session_key)

        standings = (
            self.get_meeting(country, year)["meeting_official_name"]
            + "\n"
            + str(tabulate(standings))
        )

        await ctx.send(f"```{standings}```")

    def get_meeting(self, country=None, year=None):
        if country is None or year is None:
            request = get_request(
                f"{base_url}/meetings", params={"meeting_key": "latest"}
            )
        else:
            request = get_request(
                f"{base_url}/meetings",
                params={"year": year, "country_name": country.title()},
            )

        if request.json() == []:
            raise Exception("An unexpected error occurred")
        return request.json()[0]

    def get_session(self, country=None, year=None, session_name=None):
        if session_name is None:
            session_name = "Race"
        if country is None or year is None:
            return "latest"

        request = get_request(
            f"{base_url}/sessions",
            params={
                "session_name": session_name,
                "year": year,
                "country_name": country.title(),
            },
        )

        if request.json() == []:
            raise Exception("Invalid Country Name, Year, or Session")
        return request.json()[0]["session_key"]

    async def get_standings(self, session_key="latest"):
        request = get_request(
            f"{base_url}/position",
            params={
                "session_key": session_key,
            },
        )
        if request.json() == []:
            raise Exception("An unexpected error occurred")
        stats = request.json()
        stats.reverse()
        drivers = await self.get_drivers(session_key)
        standings = [""] * len(drivers)
        counter = 1
        for position in stats:
            if standings[position["position"] - 1] == "":
                standings[position["position"] - 1] = position["driver_number"]
            elif counter == len(drivers):
                break
        return standings

    async def get_drivers(self, session_key="latest"):
        request = get_request(
            f"{base_url}/drivers",
            params={
                "session_key": session_key,
            },
        )

        if request.json()[0] is None:
            return "null"
        return list(request.json())

    async def standings_format(self, standings=[], session_key="latest"):
        table = [[], ["Standings", "Driver", "Team", "Qual Time"]]
        counter = 1

        all_laps = await self.get_time_info(session_key)
        all_qual_time = {driver: [] for driver in standings}
        driver_details = await self.get_driver_details(session_key)
        driver_details = {
            driver["driver_number"]: (driver["broadcast_name"], driver["team_name"])
            for driver in driver_details
        }

        for lap in all_laps:
            if lap["lap_duration"] is not None:
                all_qual_time[lap["driver_number"]].append(lap["lap_duration"])

        for driver in standings:
            if all_qual_time[driver] == []:
                all_qual_time[driver] = [0]
            qual_time = timedelta(seconds=min(all_qual_time[driver]))
            table.append(
                [
                    counter,
                    driver_details[driver][0].title(),
                    driver_details[driver][1],
                    qual_time,
                ]
            )
            counter += 1
        return table

    async def get_time_info(self, session_key="latest"):
        request = get_request(f"{base_url}/laps", params={"session_key": session_key})
        if request.status_code == 200:
            rp = request.json()
            if rp == []:
                raise Exception("An unexpected error occurred")

        return list(request.json())

    async def get_driver_details(self, session_key="latest"):
        request = get_request(
            f"{base_url}/drivers",
            params={
                "session_key": session_key,
            },
        )
        if request.status_code == 200:
            rp = request.json()
            if rp == []:
                raise Exception("An unexpected error occurred")
        return list(request.json())


async def setup(bot: Bot):
    await bot.add_cog(F1(bot))
