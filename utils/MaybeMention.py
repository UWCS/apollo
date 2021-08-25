from models.user import User
from discord.ext.commands import Converter

from utils.utils import get_database_user_from_id

from typing import Union
import re

__all__ = ["MentionConverter"]


#if the argument is a mention, see if a corresponding user exists in the database. else, return the string.
class MaybeMention(Converter):
    async def convert(self, ctx, argument) -> Union[User, str]:
        try:
            id = re.match(r"<@!?(?P<id>\d+)>",argument).group('id')
            member = get_database_user_from_id(int(id))
            if member is None:
                return argument
            return member
        except:
            return argument
