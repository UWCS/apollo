from decimal import Decimal, InvalidOperation
from typing import Iterable, Sized

import discord
from discord.ext.commands import CommandError, Context

from config import CONFIG


def user_is_irc_bot(ctx):
    return ctx.author.id == CONFIG.UWCS_DISCORD_BRIDGE_BOT_ID


def get_name_string(message):
    # if message.clean_content.startswith("**<"): <-- FOR TESTING
    if user_is_irc_bot(message):
        return message.clean_content.split(" ")[0][3:-3]
    else:
        return f"{message.author.mention}"


def is_decimal(num):
    try:
        Decimal(num)
        return True
    except (InvalidOperation, TypeError):
        return False


def pluralise(l, word, single="", plural="s"):
    if len(l) > 1:
        return word + plural
    else:
        return word + single


def filter_out_none(iterable: Iterable):
    return [i for i in iterable if i is not None]


def format_list(el: list):
    if len(el) == 1:
        return el[0]
    elif len(el) == 2:
        return f"{el[0]} and {el[1]}"
    else:
        return f'{", ".join(el[:-1])}, and {el[-1]}'


class AdminError(CommandError):
    message = None

    def __init__(self, message=None, *args):
        self.message = message
        super().__init__(*args)


class EnumGet:
    """Only use this if you're an enum inheriting it!"""

    @classmethod
    def get(cls, argument: str, default=None):
        values = {e.name.casefold(): e.name for e in list(cls)}
        casefolded = argument.casefold()
        if casefolded not in values:
            return default
        else:
            return cls[values[casefolded]]


async def is_compsoc_exec_in_guild(ctx: Context):
    """Check whether a member is an exec in the UWCS Discord"""
    compsoc_guild = next(
        (guild for guild in ctx.bot.guilds if guild.id == CONFIG.UWCS_DISCORD_ID), None
    )
    if not compsoc_guild:
        return False
    compsoc_member = compsoc_guild.get_member(ctx.message.author.id)
    if not compsoc_member:
        return False

    roles = [
        discord.utils.get(compsoc_member.roles, id=x) for x in CONFIG.UWCS_EXEC_ROLE_IDS
    ]
    return any(roles)
