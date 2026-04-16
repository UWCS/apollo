from enum import Enum
from typing import Any, Type, TypeVar

from discord.ext.commands import AutoShardedBot, Bot, Context, Converter
from discord.ext.commands.converter import MemberConverter

import utils

T = TypeVar("T", bound="Mention")

class MentionType(Enum):
    ID = 0
    STRING = 1


class Mention:
    def __init__(self, type: MentionType, id: int | None, string: str | None) -> None:
        self.type = type
        self.id = id
        self.string = string

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Mention):
            return NotImplemented
        return (
            self.type == other.type
            and self.id == other.id
            and self.string == other.string
        )

    def is_id_type(self) -> bool:
        return self.type == MentionType.ID

    @classmethod
    def id_mention(cls: Type[T], id: int) -> T:
        return cls(MentionType.ID, id, None)

    @classmethod
    def string_mention(cls: Type[T], string: str) -> T:
        return cls(MentionType.STRING, None, string)


class MentionConverter(Converter[Any]):
    async def convert(
        self,
        ctx: Context[Bot | AutoShardedBot],
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
