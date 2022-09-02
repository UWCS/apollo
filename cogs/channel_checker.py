import asyncio
import difflib

import discord
from discord.ext.commands import Bot, Cog

from config import CONFIG


def locate(channel_id, channel_list):
    """Find the channel from id, and create location string ("between #abc and #def")"""
    for i, c in enumerate(channel_list):
        if c.id == channel_id:
            if i == 0:
                msg = f"before {channel_list[1].mention}"
            elif i == len(channel_list) - 1:
                msg = f"after {channel_list[len(channel_list)-2].mention}"
            else:
                msg = (
                    f"between {channel_list[i-1].mention} "
                    f"and {channel_list[i+1].mention}"
                )
            return c, msg
    return None, "somewhere"


def discord_channel_key(channel):
    """Sort key for channels following the same order the Discord client does (in a guild)"""
    # Based on https://github.com/Rapptz/discord.py/issues/2392#issuecomment-707455919
    if isinstance(channel, discord.CategoryChannel):
        return channel.position, -1
    return (
        channel.category.position,
        1 if isinstance(channel, discord.VoiceChannel) else 0,  # Text before voice
        channel.position,
        channel.id,
    )


async def channel_check(bot):
    """Periodically checks for channels that have been reordered"""
    await bot.wait_until_ready()

    guild = bot.get_guild(CONFIG.UWCS_DISCORD_ID)
    channel = bot.get_channel(CONFIG.UWCS_EXEC_SPAM_CHANNEL_ID)

    previous = sorted(guild.channels, key=discord_channel_key)
    while not bot.is_closed():
        await asyncio.sleep(CONFIG.CHANNEL_CHECK_INTERVAL)

        # Get channel ids for diff
        current = sorted(guild.channels, key=discord_channel_key)
        curr_channels = [c.id for c in current]
        prev_channels = [c.id for c in previous]

        if curr_channels == prev_channels:
            continue

        # Find and filter changes
        changes = list(difflib.Differ().compare(prev_channels, curr_channels))

        # Each line after Differ will start with 2 char code
        added = [c[2:] for c in changes if c.startswith("+ ")]
        removed = [c[2:] for c in changes if c.startswith("- ")]

        moved = [int(c) for c in added if c in removed]  # Moved if added and removed

        # Construct message
        if moved:
            msg = "**⚠️ Channel Moved:**"

            if moved:
                for channel_id in moved:
                    c, prev_pos_str = locate(channel_id, previous)
                    c, curr_pos_str = locate(channel_id, current)
                    msg += f"\n\t{c.mention} has been moved from {prev_pos_str} to {curr_pos_str}"

            await channel.send(msg)

        previous = current


class ChannelChecker(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.bot.loop.create_task(channel_check(self.bot))


async def setup(bot: Bot):
    await bot.add_cog(ChannelChecker(bot))
