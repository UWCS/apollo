import asyncio
import difflib

import discord
from discord.ext.commands import Bot, Cog
from config import CONFIG


def locate(channel_name, channel_list):
    """Find the channel from id, and create location string ("between #abc and #def")"""
    for i, c in enumerate(channel_list):
        if c.name == channel_name:
            if i == 0: return c, f"before {channel_list[1].mention}"
            if i == len(channel_list)-1: return c, f"after {channel_list[len(channel_list)-2].mention}"
            else: return c, f"between {channel_list[i-1].mention} and {channel_list[i+1].mention}"
    return None, "somewhere"


def channel_sort(channels):
    """Sort text channels into actual order"""
    channels = [c for c in channels if isinstance(c, discord.TextChannel)]
    return sorted(channels, key=lambda c: c.position)


async def channel_check(bot):
    """"""
    await bot.wait_until_ready()

    guild = bot.get_guild(CONFIG.UWCS_DISCORD_ID)
    channel = bot.get_channel(CONFIG.UWCS_EXEC_SPAM_CHANNEL_ID)

    previous = channel_sort(guild.channels)
    while not bot.is_closed():
        await asyncio.sleep(CONFIG.REMINDER_SEARCH_INTERVAL)

        # Get channel ids for diff
        current = channel_sort(guild.channels)
        curr_channels = [c.name for c in current]
        prev_channels = [c.name for c in previous]

        if curr_channels == prev_channels: continue

        # Find and filter changes
        changes = list(difflib.Differ().compare(prev_channels, curr_channels))

        added = [c.strip("+ ") for c in changes if c[0] == "+"]
        removed = [c.strip("- ") for c in changes if c[0] == "-"]

        moved = [c for c in added if c in removed]  # Moved if added and removed

        # Construct message
        if moved:
            msg = "**Channel Moved:**"

            if moved:
                for channel_name in moved:
                    c, prev_pos_str = locate(channel_name, previous)
                    c, curr_pos_str = locate(channel_name, current)
                    msg += f"\n\t{c.mention} has been moved from {prev_pos_str} to {curr_pos_str}"

            await channel.send(msg)

        previous = current


class ChannelChecker(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.bot.loop.create_task(channel_check(self.bot))


def setup(bot: Bot):
    bot.add_cog(ChannelChecker(bot))
