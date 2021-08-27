from enum import Enum
import re
from typing import Union

from discord.ext.commands import Converter, MemberConverter

from models.user import User
from utils.utils import get_database_user_from_id

__all__ = ["MentionConverter"]


class MentionType(Enum):
    ID = (0,)
    STRING = 1


class Mention:
    def __init__(self, type, id, string):
        self.type: MentionType = type
        self.id: int = id
        self.string: str = string

    def is_id_type(self):
        return self.type == MentionType.ID

    def type_str(self):
        if self.type == MentionType.ID:
            return "id"

        return "string"


def parse_mention(string ) -> Mention:
    if re.match("^<@!?\d+>$",string):
        uid = int(re.search("\d+", string)[0])
        user = get_database_user_from_id(uid)

        if user is not None:
            return Mention(MentionType.ID, user.id, None)
    
    return Mention(MentionType.STRING, None, string)

class MentionConverter(Converter):
    async def convert(self, ctx, argument) -> Mention:
        return parse_mention(argument)
