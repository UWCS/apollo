import html

from bs4 import BeautifulSoup
from discord.ext import commands
from discord.ext.commands import Context, Bot, clean_content
from markdown import markdown

LONG_HELP_TEXT = """
Ｗｉｄｅｎｓ　ｔｈｅ　ｌａｓｔ　ｏｒ　ｇｉｖｅｎ　ｔｅｘｔ　ｍｅｓｓａｇｅ.
"""

SHORT_HELP_TEXT = """Ｗｉｄｅｎｓ　ｔｈｅ　ｌａｓｔ　ｏｒ　ｇｉｖｅｎ　ｔｅｘｔ　ｍｅｓｓａｇｅ."""

WIDE_MAP = dict((i, i + 0xFEE0) for i in range(0x21, 0x7F))
WIDE_MAP[0x20] = 0x3000


def widen(s: str):
    return s.translate(WIDE_MAP)


class Widen(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def widen(self, ctx: Context, *message: clean_content):
        if message:
            target_raw = html.escape(" ".join(message))
        else:
            messages = await ctx.history(limit=2).flatten()
            target_raw = html.escape(messages[-1].clean_content)

        # Convert it to HTML and then remove all tags to get the raw text
        # A side effect of this is that any text that looks like a HTML tag will be removed
        target_html = markdown(target_raw)
        soup = BeautifulSoup(target_html, 'lxml')
        target = ''.join(soup.findAll(text=True))

        widened = widen("".join([x.lstrip('@') for x in target]))
        if len(widened) <= 2000:
            await ctx.send(widened)
        else:
            await ctx.send(widen("The output is too wide") + "　:frowning:")


def setup(bot: Bot):
    bot.add_cog(Widen(bot))
