from datetime import datetime
from typing import Any

from discord.ext.commands import AutoShardedBot, BadArgument, Bot, Context, Converter

from utils.utils import parse_time


class DateTimeConverter(Converter[Any]):
    async def convert(
        self, ctx: Context[Bot | AutoShardedBot], argument: str
    ) -> datetime:
        ret = parse_time(argument)
        if ret is None:
            raise BadArgument
        return ret
