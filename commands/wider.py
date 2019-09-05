import html

from bs4 import BeautifulSoup
from discord.ext import commands
from discord.ext.commands import Context, Bot, clean_content
from markdown import markdown

WIDER_LONG_HELP_TEXT = """
Ｗｉｄｅｎｓ　ｔｈｅ　ｌａｓｔ　ｔｅｘｔ　ｍｅｓｓａｇｅ.
"""

WIDER_SHORT_HELP_TEXT = """Ｗｉｄｅｎｓ　ｔｈｅ　ｌａｓｔ　ｔｅｘｔ　ｍｅｓｓａｇｅ."""

WIDEN_LONG_HELP_TEXT = """
Ｗ　ｉ　ｄ　ｅ　ｎ　ｓ　　　ｔ　ｈ　ｅ　　　ｇ　ｉ　ｖ　ｅ　ｎ　　　ｔ　ｅ　ｘ　ｔ　．
"""

WIDEN_SHORT_HELP_TEXT = """Ｗ　ｉ　ｄ　ｅ　ｎ　ｓ　　　ｔ　ｈ　ｅ　　　ｇ　ｉ　ｖ　ｅ　ｎ　　　ｔ　ｅ　ｘ　ｔ　．"""

WIDE_MAP = dict((i, i + 0xFEE0) for i in range(0x21, 0x7F))
WIDE_MAP[0x20] = 0x3000


def widen(s: str):
    return s.translate(WIDE_MAP)


class Wider(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(help=WIDER_LONG_HELP_TEXT, brief=WIDER_SHORT_HELP_TEXT)
    async def wider(self, ctx: Context):
        messages = await ctx.history(limit=2).flatten()
        target_raw = html.escape(messages[-1].clean_content)

        # Convert it to HTML and then remove all tags to get the raw text
        # A side effect of this is that any text that looks like a HTML tag will be removed
        target_html = markdown(target_raw)
        soup = BeautifulSoup(target_html, 'lxml')
        target = ''.join(soup.findAll(text=True))

        widened = widen(" ".join([x.lstrip('@') for x in target]))
        if len(widened) <= 2000:
            await ctx.send(widened)
        else:
            await ctx.send(widen("The output is too wide") + "　:frowning:")

    @commands.command(help=WIDEN_LONG_HELP_TEXT, brief=WIDEN_SHORT_HELP_TEXT, name="widen")
    async def _widen(self, ctx: Context, *message: clean_content):
        target_raw = html.escape("".join(message))

        # Convert it to HTML and then remove all tags to get the raw text
        # A side effect of this is that any text that looks like a HTML tag will be removed
        target_html = markdown(target_raw)
        soup = BeautifulSoup(target_html, 'lxml')
        target = ''.join(soup.findAll(text=True))

        widened = widen(" ".join([x.lstrip('@') for x in target]))
        if len(widened) <= 2000:
            await ctx.send(widened)
        else:
            await ctx.send(widen("The output is too wide") + "　:frowning:")

def setup(bot: Bot):
    bot.add_cog(Wider(bot))
