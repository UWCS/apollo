from datetime import datetime, timedelta

import discord
from discord import Color, Embed
from discord.ext.commands import Bot, Cog

from config import CONFIG


class Database(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        
    @Cog.listener()
    async def on_message(self, message: discord.Message):
        joined_recently = message.author.joined_at > datetime.now() - timedelta(days=7)
        contains_everyone = '@everyone' in message.content
        is_giving_away = 'giving away' in message.content.lower()

        if not joined_recently or not (contains_everyone or is_giving_away):
            return

        channel = self.bot.get_channel(CONFIG.UWCS_BOT_LOG_CHANNEL_ID)

        embed_colour = Color.from_rgb(61, 83, 255)
        embed_title = f'@{message.author.global_name}, ID: {message.author.id}'
        embed_description = f'User suspected to be a bot, joined_recently: {joined_recently}, contains_everyone: {contains_everyone}, is_giving_away: {is_giving_away}'
        embed = Embed(
            title=embed_title, color=embed_colour, embed_description=embed_description
        )
        
        await message.delete()
        await channel.send(f'<@&{CONFIG.UWCS_EXEC_ROLE_IDS[1]}>', embed=embed)
        await message.author.timeout(timedelta(days=1))

async def setup(bot: Bot):
    await bot.add_cog(Database(bot))