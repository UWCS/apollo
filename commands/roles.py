import re

import discord
from discord.ext import commands
from discord.ext.commands import Bot, Context

from models import db_session, RoleMessage

link_regex = re.compile(
    r"^https?://(?:(ptb|canary)\.)?discordapp\.com/channels/"
    r"(?:([0-9]{15,21})|(@me))"
    r"/(?P<channel_id>[0-9]{15,21})/(?P<message_id>[0-9]{15,21})/?$"
)


class Roles(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command()
    async def add_role_menu(self, ctx: Context):
        if not ctx.author.bot:
            await ctx.send("Please aslkdhaskhjdb")

            def check(message):
                return (
                    message.author == ctx.author
                    and message.channel == ctx.channel
                    and link_regex.match(message.content)
                )

            message = await self.bot.wait_for("message", check=check)
            match = link_regex.match(message.content)
            message_id = match.group("message_id")
            channel_id = match.group("channel_id")
            guild_id = self.bot.get_channel(int(match.group("channel_id"))).guild.id

            message = await ctx.send("Please react xd")

            def check(reaction, user):
                return reaction.message.id == message.id and user.id == ctx.author

            reaction, _ = await self.bot.wait_for("reaction_add")
            reaction_name = str(reaction.emoji)

            message = await ctx.send("ping that mofo")

            def check(message):
                return (
                    message.author == ctx.author
                    and message.channel == ctx.channel
                    and len(message.role_mentions) == 1
                )

            message = await self.bot.wait_for("message", check=check)
            role_id = message.role_mentions[0].id

            newRoleMessage = RoleMessage(
                message_id=message_id,
                channel_id=channel_id,
                guild_id=guild_id,
                reaction_name=reaction_name,
                role_id=role_id,
            )
            db_session.add(newRoleMessage)
            db_session.commit()
            db_session.flush()
            await ctx.send("all sorted fam")

    @commands.Cog.listener(name="on_raw_reaction_add")
    async def on_reaction_add(self, payload):
        message_id = payload.message_id
        channel_id = payload.channel_id
        guild_id = payload.guild_id
        reaction_name = str(payload.emoji)
        member = payload.member

        role_message = db_session.query(RoleMessage).filter(
            RoleMessage.message_id == message_id
            and RoleMessage.channel_id == channel_id
            and RoleMessage.guild_id == guild_id
            and RoleMessage.reaction_name == reaction_name
        ).first()

        if role_message:
            role = member.guild.get_role(role_message.role_id)
            await member.add_roles(role)


    @commands.Cog.listener(name="on_raw_reaction_remove")
    async def on_reaction_remove(self, payload):
        print("=" * 10, payload, "=" * 10, sep="\n")


def setup(bot: Bot):
    bot.add_cog(Roles(bot))
