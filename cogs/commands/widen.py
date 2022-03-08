import html
import re

from bs4 import BeautifulSoup
from discord.ext import commands
from discord.ext.commands import Bot, Context
from markdown import markdown

LONG_HELP_TEXT = """
Ｗｉｄｅｎｓ　ｔｈｅ　ｌａｓｔ　ｏｒ　ｇｉｖｅｎ　ｔｅｘｔ　ｍｅｓｓａｇｅ.
"""

SHORT_HELP_TEXT = """Ｗｉｄｅｎｓ　ｔｈｅ　ｌａｓｔ　ｏｒ　ｇｉｖｅｎ　ｔｅｘｔ　ｍｅｓｓａｇｅ."""

WIDE_MAP = dict((i, i + 0xFEE0) for i in range(0x21, 0x7F))
WIDE_MAP[0x20] = 0x3000


def apply_widen(s: str):
    return s.translate(WIDE_MAP)


class Widen(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT, rest_is_raw=True)
    async def widen(self, ctx: Context, *, message):
        if message:
            target_raw = message
        elif (reference := ctx.message.reference) is not None:
            m = reference.resolved
            if m is None:
                return
            target_raw = m.clean_content
            if target_raw is None:
                return
        else:
            messages = await ctx.history(limit=2).flatten()
            target_raw = messages[-1].clean_content

        target_raw = re.sub(r"<:.+:\d+>", "", target_raw)  # Remove custom emoji
        target_raw = re.sub(r"^\*\*<\w+>\*\* ", "", target_raw)  # Remove IRC usernames
        target_raw = html.escape(
            target_raw.strip()
        )  # Escape any other text in prep for de-markdownify

        # Convert it to HTML and then remove all tags to get the raw text
        # A side effect of this is that any text that looks like an HTML tag will be removed
        target_html = markdown(target_raw)
        soup = BeautifulSoup(target_html, "lxml")
        target = "".join(soup.findAll(text=True))

        # Cascade the widening
        is_wide = all(
            ord(c) in range(0xFF01, 0xFF5F) or ord(c) == 0x3000 for c in target_raw
        )
        if is_wide:
            widened = apply_widen("　".join([x.lstrip("@") for x in target]))
        else:
            widened = apply_widen("".join([x.lstrip("@") for x in target]))

        if widened:
            # Make sure we send a message that's short enough
            if len(widened) <= 2000:
                await ctx.send(widened)
            else:
                await ctx.send(apply_widen("The output is too wide") + "　:frowning:")


def setup(bot: Bot):
    bot.add_cog(Widen(bot))
