from enum import Enum
from typing import Union

from discord.ext.commands import Converter
from discord.ext.commands.converter import MemberConverter

import utils

__all__ = ["MentionType", "Mention", "MentionConverter"]


class MentionType(Enum):
    ID = 0
    STRING = 1


class Mention:
    def __init__(self, type, id, string):
        self.type: MentionType = type
        self.id: int = id
        self.string: str = string

    def __eq__(self, other_m):
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
    def id_mention(id):
        return Mention(MentionType.ID, id, None)

    @staticmethod
    def string_mention(string):
        return Mention(MentionType.STRING, None, string)


class MentionConverter(Converter):
    async def convert(self, ctx, string) -> Mention:
        member_converter = MemberConverter()
        try:
            discord_user = await member_converter.convert(ctx, string)
            uid = utils.get_database_user_from_id(discord_user.id)

            if uid is not None:
                return Mention.id_mention(uid.id)
            return Mention.string_mention(string)
        except:
            return Mention.string_mention(string)
