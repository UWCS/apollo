from textwrap import dedent
from typing import Optional

from discord import Member
from discord.ext.commands import Bot, Cog, Context, Greedy, check, command
from discord.utils import get

from utils import AdminError, format_list, is_compsoc_exec_in_guild


class Moderation(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self._emoji = None

    @property
    def emoji(self):
        if self._emoji is None:
            self._emoji = {
                "no": get(self.bot.emojis, id=840911865830703124),
                "what": get(self.bot.emojis, id=840917271111008266),
            }
        return self._emoji

    def only_mentions_users(self, react=False):
        async def predicate(ctx):
            ret = not (
                ctx.message.mention_everyone or len(ctx.message.role_mentions) > 0
            )
            if not ret and react:
                await ctx.message.add_reaction(self.emoji["no"])
            return ret

        return check(predicate)

    async def cog_check(self, ctx):
        if not await is_compsoc_exec_in_guild(ctx):
            raise AdminError("You don't have permission to run this command.")
        return True

    async def cog_command_error(self, ctx, error):
        await ctx.message.add_reaction(self.emoji["no"])

    @command()
    @only_mentions_users(True)
    async def ban(
        self,
        ctx: Context,
        members: Greedy[Member],
        delete_days: Optional[int] = 0,
        *,
        reason: Optional[str],
    ):
        if len(members) == 0:
            await ctx.message.add_reaction(self.emoji["what"])
            return

        mentions = format_list([member.mention for member in members])
        messages_deleted = (
            "No messages were deleted."
            if delete_days == 0
            else f"Messages sent in the last {delete_days} day{'s' if delete_days != 1 else ''} were deleted."
        )
        with_reason = (
            "with no reason given."
            if reason is None
            else f"with the reason\n> {reason}"
        )
        were = "were" if len(members) > 1 else "was"

        for member in members:
            member.ban(reason=reason, delete_message_days=delete_days)

        await ctx.send(
            dedent(
                f"""
                :hammer: **BANNED** :hammer:
                {mentions} {were} banned {with_reason}
                {messages_deleted}
                """
            )
        )

    @command()
    @only_mentions_users(True)
    async def kick(self, ctx: Context, members: Greedy[Member], *, reason: Optional[str]):
        if len(members) == 0:
            await ctx.message.add_reaction(self.emoji["what"])

        mentions = format([member.mention for member in members])
        with_reason = (
            "with no reason given"
            if reason is None
            else f"with the reason \n> {reason}"
        )
        were = "were" if len(members) > 1 else "was"

        for member in members:
            member.kick(reason=reason)

        await ctx.send(
            dedent(
                f"""
                :leg: **KICKED** :leg:
                {mentions} {were} kicked {with_reason}
                """
            )
        )


def setup(bot: Bot):
    bot.add_cog(Moderation(bot))
