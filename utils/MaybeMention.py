from models.user import User
from discord.ext.commands import Converter, MemberConverter

from utils.utils import get_database_user_from_id

from typing import Union
import re

__all__ = ["MentionConverter"]


# return one of the following in descending order:
# a user from the database
# the username as a string
# the mention as a string
class MaybeMention(Converter):
    async def convert(self, ctx, argument) -> Union[User, str]:
        try:
            member = await MemberConverter().convert(ctx, argument)
            user = get_database_user_from_id(int(member.id))

            if user is None:
                return member.name

            return user
        except:
            return argument
