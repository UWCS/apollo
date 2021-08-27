from enum import Enum
from typing import Union

from discord.ext.commands import Converter, MemberConverter

from models.user import User
from utils.utils import get_database_user_from_id

__all__ = ["MentionConverter"]

class Mention:
    def Mention(self,type,id,string):
        self.type   :str = type
        self.id     :int = id
        self.string :str = string

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
                return Mention("string",None,member.name)

            return Mention("id",user,None)
        except:
            return Mention("string",None,argument)
