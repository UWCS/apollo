from typing import Any, Awaitable, Callable, Protocol, TypeAlias, TypeGuard

from discord import Guild, Interaction, Message
from discord.abc import Messageable
from discord.ext.commands import Context

Callback = Callable[..., Awaitable[Any]]

JSON: TypeAlias = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None

def is_context(obj: object) -> TypeGuard[Context[Any]]:
    return isinstance(obj, Context)

class GuildChannelMessageable(Protocol):
    guild: Guild
    async def send(self, **kwargs: Any) -> Message: ...

class ModalCtx(Protocol):
    channel: Messageable
    message: Message
    interaction: Interaction
    bot: Any

    async def reply(self, content: str | None = None, **kwargs: Any) -> Message: ...