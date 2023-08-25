from enum import Enum
from typing import Any

from discord.ext import commands
from discord.ext.commands.converter import MemberConverter

import utils


class MentionType(Enum):
    ID = 0
    STRING = 1


class Mention:
    def __init__(self, type: MentionType, id: int | None, string: str | None):
        self.type = type
        self.id = id
        self.string = string

    def __eq__(self, other_m: object) -> bool:
        if not isinstance(other_m, Mention):
            return False
        return all(
            [
                self.type == other_m.type,
                self.id == other_m.id,
                self.string == other_m.string,
            ]
        )

    def is_id_type(self):
        return self.type == MentionType.ID

    @staticmethod
    def id_mention(id: int):
        return Mention(MentionType.ID, id, None)

    @staticmethod
    def string_mention(string: str):
        return Mention(MentionType.STRING, None, string)


class MentionConverter(commands.Converter[Any]):
    async def convert(
        self,
        ctx: commands.Context[commands.Bot | commands.AutoShardedBot],
        argument: str,
    ) -> Mention:
        member_converter = MemberConverter()
        try:
            discord_user = await member_converter.convert(ctx, argument)
            uid = utils.get_database_user_from_id(discord_user.id)

            if uid is not None:
                return Mention.id_mention(uid.id)
            return Mention.string_mention(argument)
        except Exception:
            return Mention.string_mention(argument)
