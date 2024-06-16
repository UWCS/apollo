from discord.ext import commands, tasks
from discord.ext.commands import Bot
from feedparser import parse

FEEDS = [
    "https://warwick.ac.uk/sitebuilder2/api/rss/news.rss?page=/fac/sci/dcs/news/&rss=true",
    "https://warwick.ac.uk/sitebuilder2/api/rss/news.rss?page=/fac/sci/dcs/events/&rss=true&view=latest",
    "https://warwick.ac.uk/sitebuilder2/api/rss/news.rss?page=/fac/sci/dcs/teaching/studentevents/&rss=true&view=latest",
    "https://warwick.ac.uk/sitebuilder2/api/rss/news.rss?page=/fac/sci/dcs/teaching/announcements/&rss=true",
    "https://warwick.ac.uk/sitebuilder2/api/rss/news.rss?page=/fac/sci/dcs/teaching/dcsnoticeboard/&rss=true",
]
CHANNEL = 1247565016069308607


class RSS(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.rss_loop.start()

    @tasks.loop(hours=24)
    async def rss_loop(self):
        post_channel = self.bot.get_channel(CHANNEL)
        for feed in FEEDS:
            parsed = parse(feed)
            message = f"From {parsed.feed.title}\n"
            for entry in parsed.entries:
                # if INSERT_WAY_OF_DISTINGUISHING_NEW_POSTS_HERE:
                message += f"[{entry.title}]({entry.link}) on {entry.published}\n"


async def setup(bot: Bot):
    await bot.add_cog(RSS(bot))
