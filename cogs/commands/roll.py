import random
import re
from dataclasses import dataclass
from enum import Enum
from functools import cached_property

from discord.ext import commands
from discord.ext.commands import (
    BadArgument,
    Bot,
    Context,
    Converter,
    Greedy,
    clean_content,
)
from parsita import ParseError, TextParsers, lit, opt, reg, rep
from parsita.util import constant

from utils import get_name_string
from utils.exceptions import OutputTooLargeError

LONG_HELP_TEXT = """
Rolls an unbiased xdy (x dice with y sides).

If no dice are specified, it will roll a single 1d6 (one 6-sided die).
____________________________________________________________

- !r                  | (rolls a 1d6)
- !r 1d6              | (an explicitly-defined 1d6)
- !r d6               | (omitted dice counts default to 1)
- !r 1d6 + 5          | (supports +, -, *, /, ^)
- !r (1d6+1)+(1d6*10) | (supports brackets)
- !r (1d6)d(1d6)      | (supports nested rolls)
____________________________________________________________

Note: using division returns a floating point value and is prone to errors.
"""

SHORT_HELP_TEXT = """Rolls an unbiased xdy (x dice with y sides)"""

SUCCESS_OUT = """
:game_die: **DICE TIME** :game_die:
{ping}
{body}
"""

FAILURE_OUT = """
:warning: **DICE UNDERMINE** :warning:
{ping}
{body}
"""

WARNING_OUT = """
:no_entry_sign: **DICE CRIME** :no_entry_sign:
{ping}
{body}
"""


def clean_brackets(string):
    return string[1:-1] if string[0] == "(" and string[-1] == ")" else string


class Roll(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(
        help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT, aliases=["r"], rest_is_raw=True
    )
    async def roll(self, ctx: Context, *, message: clean_content):
        display_name = get_name_string(ctx.message)
        if len(message) == 0:
            message = "1d6"
        message = message.strip()
        try:
            expression = DiceParser.parse_all.parse(message).or_die()
        except ParseError as e:
            await ctx.send(FAILURE_OUT.format(ping=display_name, body=f"```{e}```"))
            return
        except ExcessiveDiceRollsError:
            await ctx.send(
                WARNING_OUT.format(
                    ping=display_name,
                    body="_You requested an excessive number of dice rolls._",
                )
            )
            return
        value = expression.value
        try:
            out = SUCCESS_OUT.format(
                ping=display_name,
                body=f"`{repr(expression)}` | **{value}** ⟵ {clean_brackets(str(expression))}",
            )
            await ctx.send(out)
        except OutputTooLargeError:
            await ctx.send(
                WARNING_OUT.format(
                    ping=display_name, body="_Your output was too large!_"
                )
            )


class ValueConstant:
    def __init__(self, value):
        self.value = value
        self.roll_count = 0

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return str(self.value)


class ValueRoll:
    def __init__(self, count, sides):
        self.roll_count = count.value
        if self.roll_count > 1000:
            raise ExcessiveDiceRollsError
        self.count = count
        self.sides = sides
        if sides.value == 1:
            self.rolls = [1] * count.value
        else:
            self.rolls = random.choices(range(1, sides.value + 1), k=count.value)
        self.value = sum(self.rolls)

    def __str__(self):
        out = str(self.rolls)
        if len(out) > 2000:
            raise OutputTooLargeError
        return out

    def __repr__(self):
        return f"{self.count}d{self.sides}"


class BinaryOperator:
    def __init__(self, op, lhs, rhs):
        self.roll_count = lhs.roll_count + rhs.roll_count
        if self.roll_count > 1000:
            raise ExcessiveDiceRollsError
        self.op = op
        self.lhs = lhs
        self.rhs = rhs
        mapping = {
            RollOperator.ADD: lhs.value + rhs.value,
            RollOperator.SUB: lhs.value - rhs.value,
            RollOperator.MUL: lhs.value * rhs.value,
            RollOperator.DIV: lhs.value / rhs.value,
            RollOperator.POW: lhs.value ** rhs.value,
        }
        self.value = mapping[self.op]

    def __str__(self):
        out = f"({self.lhs}{self.op}{self.rhs})"
        if len(out) > 2000:
            raise OutputTooLargeError
        return out

    def __repr__(self):
        return f"({repr(self.lhs)}{self.op}{repr(self.rhs)})"


class RollOperator(Enum):
    ADD = "+"
    SUB = "-"
    MUL = "*"
    DIV = "/"
    POW = "^"

    def __str__(self):
        mapping = {
            RollOperator.ADD: "+",
            RollOperator.SUB: "-",
            RollOperator.MUL: "*",
            RollOperator.DIV: "/",
            RollOperator.POW: "^",
        }
        return mapping[self]


class DiceParser(TextParsers):
    nat = reg(r"[1-9]\d*") > int

    constant = reg(r"\d+") > (lambda x: ValueConstant(int(x)))
    roll = die_value << "d" & die_value > (lambda xs: ValueRoll(xs[0], xs[1]))
    naked_roll = "d" >> die_value > (lambda x: ValueRoll(ValueConstant(1), x))

    value = roll | naked_roll | constant | brackets
    die_value = constant | brackets

    op_add = value << "+" & expr > (
        lambda xs: BinaryOperator(RollOperator.ADD, xs[0], xs[1])
    )
    op_sub = value << "-" & expr > (
        lambda xs: BinaryOperator(RollOperator.SUB, xs[0], xs[1])
    )
    op_mul = value << "*" & expr > (
        lambda xs: BinaryOperator(RollOperator.MUL, xs[0], xs[1])
    )
    op_div = value << "/" & expr > (
        lambda xs: BinaryOperator(RollOperator.DIV, xs[0], xs[1])
    )
    op_pow = value << "^" & expr > (
        lambda xs: BinaryOperator(RollOperator.POW, xs[0], xs[1])
    )

    expr = op_add | op_sub | op_mul | op_div | op_pow | value
    brackets = "(" >> expr << ")"

    parse_all = expr


class ExcessiveDiceRollsError(Exception):
    """Raised when too many dice are rolled in a single command"""


def setup(bot: Bot):
    bot.add_cog(Roll(bot))
