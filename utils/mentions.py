import re
from enum import Enum

from discord.ext.commands import Converter

from models import db_session
from models.user import User

__all__ = ["MentionType","Mention","parse_mention","MentionConverter"]


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

    def type_str(self):
        if self.type == MentionType.ID:
            return "id"

        return "string"


def parse_mention(string, db_session=db_session) -> Mention:
    if string is None:
        return None
    if re.match("^<@!?\d+>$", string):
        uid = int(re.search("\d+", string)[0])
        user = db_session.query(User).filter(User.user_uid == uid).one_or_none()

        if user is not None:
            return Mention(MentionType.ID, user.id, None)

    return Mention(MentionType.STRING, None, string)


class MentionConverter(Converter):
    async def convert(self, ctx, argument) -> Mention:
        return parse_mention(argument)
