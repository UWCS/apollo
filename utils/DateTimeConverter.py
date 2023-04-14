from discord.ext.commands import BadArgument, Converter, Context, Bot, AutoShardedBot
from typing import Any
from utils.utils import parse_time
from datetime import datetime


class DateTimeConverter(Converter[Any]):
    async def convert(self, ctx: Context[Bot | AutoShardedBot], argument: str) -> datetime:
        ret = parse_time(argument)
        if ret is None:
            raise BadArgument
        return ret
