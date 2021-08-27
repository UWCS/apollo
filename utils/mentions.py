from enum import Enum
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


# return one of the following in descending order:
# a user from the database
# the username as a string
# the mention as a string
class MentionConverter(Converter):
    async def convert(self, ctx, argument) -> Mention:
        try:
            member = await MemberConverter().convert(ctx, argument)
            user = get_database_user_from_id(int(member.id))

            if user is None:
                return Mention(MentionType.STRING, None, member.name)

            return Mention(MentionType.ID, user.id, None)
        except:
            return Mention(MentionType.STRING, None, argument)
