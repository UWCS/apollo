import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Iterable

import dateparser
import discord
from discord.ext.commands import CommandError, Context
from more_itertools import partition

import models
from config import CONFIG
from models import db_session
from utils.typing import Identifiable

__all__ = [
    "AdminError",
    "EnumGet",
    "clean_brackets",
    "filter_out_none",
    "format_list",
    "format_list_of_members",
    "get_database_user_from_id",
    "get_database_user",
    "get_name_string",
    "is_compsoc_exec_in_guild",
    "is_decimal",
    "parse_time",
    "partition_list",
    "pluralise",
    "user_is_irc_bot",
]


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


def clean_brackets(
    string,
    brackets=(("(", ")"),),
):
    """Removes matching brackets from the outside of a string
    Only supports single-character brackets
    """
    while len(string) > 1 and (string[0], string[-1]) in brackets:
        string = string[1:-1]
    return string


def filter_out_none(iterable: Iterable, /):
    return (i for i in iterable if i is not None)


def format_list(el: list, /):
    if len(el) == 1:
        return f"{el[0]}"
    elif len(el) == 2:
        return f"{el[0]} and {el[1]}"
    else:
        return f'{", ".join(el[:-1])}, and {el[-1]}'


def format_list_of_members(members, /, *, ping=True):
    if ping:
        el = [member.mention for member in members]
    else:
        el = [str(member) for member in members]
    return format_list(el)


def get_database_user_from_id(id_: int, /) -> models.User:
    return (
        db_session.query(models.User).filter(models.User.user_uid == id_).one_or_none()
    )


def get_database_user(user: Identifiable, /) -> models.User:
    return get_database_user_from_id(user.id)


def get_name_string(message):
    # if message.clean_content.startswith("**<"): <-- FOR TESTING
    if user_is_irc_bot(message):
        return message.clean_content.split(" ")[0][3:-3]
    else:
        return f"{message.author.mention}"


async def is_compsoc_exec_in_guild(ctx: Context, /):
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


def is_decimal(num):
    try:
        Decimal(num)
        return True
    except (InvalidOperation, TypeError):
        return False


def parse_time(time, /):
    # dateparser.parse returns None if it cannot parse
    parsed_time = dateparser.parse(
        time, settings={"DATE_ORDER": "DMY", "PREFER_DATES_FROM": "future"}
    )

    now = datetime.now()

    if not parsed_time:
        try:
            parsed_time = datetime.strptime(time, "%Y-%m-%d %H:%M")
        except ValueError:
            pass

    if not parsed_time:
        try:
            parsed_time = datetime.strptime(time, "%m-%d %H:%M")
            parsed_time = parsed_time.replace(year=now.year)
            if parsed_time < now:
                parsed_time = parsed_time.replace(year=now.year + 1)
        except ValueError:
            pass

    if not parsed_time:
        try:
            parsed_time = datetime.strptime(time, "%H:%M:%S")
            parsed_time = parsed_time.replace(
                year=now.year, month=now.month, day=now.day
            )
            if parsed_time < now:
                parsed_time = parsed_time + timedelta(days=1)

        except ValueError:
            pass

    if not parsed_time:
        try:
            parsed_time = datetime.strptime(time, "%H:%M")
            parsed_time = parsed_time.replace(
                year=now.year, month=now.month, day=now.day
            )
            if parsed_time < now:
                parsed_time = parsed_time + timedelta(days=1)
        except ValueError:
            pass

    if not parsed_time:
        result = re.match(r"(\d+d)?\s*(\d+h)?\s*(\d+m)?\s*(\d+s)?(?!^)$", time)
        if result:
            parsed_time = now
            if result.group(1):
                parsed_time = parsed_time + timedelta(days=int(result.group(1)[:-1]))
            if result.group(2):
                parsed_time = parsed_time + timedelta(hours=int(result.group(2)[:-1]))
            if result.group(3):
                parsed_time = parsed_time + timedelta(minutes=int(result.group(3)[:-1]))
            if result.group(4):
                parsed_time = parsed_time + timedelta(seconds=int(result.group(4)[:-1]))

    return parsed_time


def partition_list(pred, el, /):
    a, b = partition(pred, el)
    return list(a), list(b)


def pluralise(el, /, word, single="", plural="s"):
    if len(el) > 1:
        return word + plural
    else:
        return word + single


def user_is_irc_bot(ctx):
    return ctx.author.id == CONFIG.UWCS_DISCORD_BRIDGE_BOT_ID
