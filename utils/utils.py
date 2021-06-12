from decimal import Decimal, InvalidOperation
from typing import Iterable

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


def clean_brackets(
    str,
    brackets=[
        ("(", ")"),
    ],
):
    """Removes matching brackets from the outside of a string
    Only supports single-character brackets
    """
    while len(str) > 1 and (str[0], str[-1]) in brackets:
        str = str[1:-1]
    return str
