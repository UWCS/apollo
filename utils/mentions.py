from enum import Enum

from discord.ext.commands import Converter
from discord.ext.commands.converter import MemberConverter

import utils
from models import db_session
from models.user import User

__all__ = ["MakeMention", "MentionType", "Mention", "MentionConverter"]


class MentionType(Enum):
    ID = 0
    STRING = 1


class Mention:
    def __init__(self, type, id, string):
        self.type: MentionType = type
        self.id: int = id
        self.string: str = string

    def is_id_type(self):
        return self.type == MentionType.ID


class MakeMention:
    def id_mention(id):
        return Mention(MentionType.ID, id, None)

    def string_mention(string):
        return Mention(MentionType.STRING, None, string)

class MentionConverter(Converter):
    async def convert(self,ctx, obj) -> Mention:
        if obj is None:
            return None

        try:
            member_converter = MemberConverter()
            discord_user = await member_converter.convert(ctx,obj)
            uid = utils.get_database_user_from_id(discord_user.id)

            if uid is not None:
                return MakeMention.id_mention(uid.id)
        except:
            return MakeMention.string_mention(obj)
        return MakeMention.string_mention(obj)
