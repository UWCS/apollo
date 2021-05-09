import re
from random import randint

from discord.ext import commands
from discord.ext.commands import Bot, Context, clean_content

from utils import get_name_string

LONG_HELP_TEXT = """
Rolls an unbiased xdy (x dice with y sides).

If no dice are specified, it will roll a single 1d6 (one 6-sided die).

Multiple dice can be specified:
"!roll 1d6 2d5 3d4" - will roll one 6-sided die, two 5-sided dice, and three 4-sided dice.
"""

SHORT_HELP_TEXT = """Rolls an unbiased xdy (x dice with y sides)"""


def roll_dice(count, sides):
    if sides == 1:
        return [count]
    results = []
    for i in range(count):
        results.append(randint(1, sides))
    return results


def format_roll(roll):
    data = [int(x) for x in roll.split("d")]
    results = roll_dice(data[0], data[1])
    return f"`{roll}` | {sum(results)} ⟵ {results}"


class Roll(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.pattern = re.compile("^\d+d\d+$")

    @commands.command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT, aliases=["r"])
    async def roll(self, ctx: Context, *message: clean_content):
        display_name = get_name_string(ctx.message)
        if len(message) == 0:
            rolls = ["1d6"]
        else:
            rolls = [
                roll
                for roll in message
                if self.pattern.search(roll)
                and int(roll.split("d")[0]) > 0
                and int(roll.split("d")[1]) > 0
            ]
            if len(rolls) == 0:
                await ctx.send(
                    f"Please give rolls in the form `xdy` (e.g. `1d6`), where x and y are positive {display_name}."
                )
                return
            # if any(map(lambda roll : int(roll.split("d")[0]) > 1000, rolls)):
            if sum(map(lambda roll: int(roll.split("d")[0]), rolls)) > 1000:
                await ctx.send(
                    f"Please do not request excessively long dice rolls, {display_name}."
                )
                return
        lines = [f":game_die: **DICE TIME** :game_die:\n{display_name}"] + [
            format_roll(roll) for roll in rolls
        ]
        if len(message) > 0 and len(rolls) != len(message):
            lines += [
                "\n**Note:** I didn't understand all of the inputs provided.\nPlease give rolls in the form `xdy` (e.g. `1d6`), where x and y are positive."
            ]
        out = "\n".join(lines)
        if len(out) > 2000:
            await ctx.send(
                f":no_entry_sign: **DICE CRIME** :no_entry_sign:\n_Your result was too long to fit in a single message, {display_name}!_"
            )
        else:
            await ctx.send(out)


def setup(bot: Bot):
    bot.add_cog(Roll(bot))
