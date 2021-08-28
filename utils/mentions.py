import re
from enum import Enum

from discord.ext.commands import Converter

from models import db_session
from models.user import User

__all__ = ["MakeMention", "MentionType", "Mention", "parse_mention", "MentionConverter"]


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


def parse_mention(string, db_session=db_session) -> Mention:
    if string is None:
        return None
    if re.match("^<@!?\d+>$", string):
        uid = int(re.search("\d+", string)[0])
        user = db_session.query(User).filter(User.user_uid == uid).one_or_none()

        if user is not None:
            return MakeMention.id_mention(user.id)

    return MakeMention.string_mention(string)


class MentionConverter(Converter):
    async def convert(self, ctx, argument) -> Mention:
        return parse_mention(argument)
