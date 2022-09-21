from typing import List, NamedTuple

import discord
from discord.ext import commands
from discord import AllowedMentions, ButtonStyle, InteractionMessage, Role
from discord.ext.commands import Context, Bot
from discord.ui import Button, View
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from models import User, db_session
from models.role_menu import RoleMenu, RoleEntry

DENSE_ARRANGE = True
Chunk = NamedTuple("Chunk", [("start", int), ("end", int), ("choices", List[str])])

# Records last ephemeral message to each user, so can edit for future votes
class RoleButton(Button):
    def __init__(self, interface, role: discord.Role, emoji: str):
        super().__init__(label=role.name, emoji=emoji)
        self.role = role
        self.interface = interface

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        if self.role not in user.roles: await user.add_roles(self.role, reason="Button Role")
        else: await user.remove_roles(self.role, reason="Button Role")


class RoleMenuCog(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_group()
    async def roles(self, ctx: Context):
        if not ctx.invoked_subcommand:
            await ctx.send("Subcommand not found")

    @roles.command()
    async def create(self, ctx: Context, msg_ref: str, title: str, channel: discord.TextChannel, description: str = None):
        msg = None
        try:
            text = f"**{title}**"
            if description:
                text += f"\n{description}\n"
            msg = await channel.send(text)
            menu = RoleMenu(msg_ref=msg_ref, guild_id=ctx.guild.id, title=title, channel_id=channel.id, message_id=msg.id)
            db_session.add(menu)
            db_session.commit()
            await ctx.send(f"Role Menu `{msg_ref}` created in {channel.mention}")

        except IntegrityError:
            db_session.rollback()
            await ctx.send(f"A Role Menu with reference `{msg_ref}` already exists in this server.")

        except SQLAlchemyError:
            db_session.rollback()
            await ctx.send("Database error creating menu")
            raise
    
    @roles.command()
    async def add(self, ctx, msg_reference, emoji: str, role: discord.Role, *, description=None):
        # Fetch data
        guild: discord.Guild = ctx.guild
        menu = self.get_menu(guild.id, msg_reference)
        if not menu: raise Exception(f"No message exists with reference `{msg_reference}`.")

        # Edit embed to include new option
        channel = guild.get_channel(menu.channel_id)
        message: discord.Message = await channel.fetch_message(menu.message_id)

        new_content = f"{message.content}\n_ _\n{emoji} for **{role.name}** {description}"
        view = View.from_message(message)
        view.add_item(RoleButton(self, role, emoji))

        try:
            entry = RoleEntry(menu_id=menu.id, role=role.id, title=role.name, description=description, emoji=str(role))
            db_session.add(entry)
            db_session.commit()
        except SQLAlchemyError:
            db_session.rollback()
            await ctx.send("Database error creating menu")
            raise

        await message.edit(content=new_content, view=view)
        await ctx.send(f"Button for role {role.name} added to `{msg_reference}`", ephemeral=True)

    
    @roles.command()
    async def add_text(self, ctx, msg_reference, *, text):
        # Fetch data
        guild: discord.Guild = ctx.guild
        menu = self.get_menu(guild.id, msg_reference)
        if not menu: raise Exception(f"No message exists with reference `{msg_reference}`.")

        # Edit embed to include new option
        channel = guild.get_channel(menu.channel_id)
        message: discord.Message = await channel.fetch_message(menu.message_id)

        new_content = f"{message.content}{text}"
        await message.edit(content=new_content)
        await ctx.send(f"Text added to `{msg_reference}`", ephemeral=True)

    def get_menu(self, guild_id, ref):
        """Finds message data for RR from ref"""
        return (db_session.query(RoleMenu)
            .filter(RoleMenu.msg_ref == ref)
            .filter(RoleMenu.guild_id == guild_id)
            .one_or_none())


async def setup(bot: Bot):
    await bot.add_cog(RoleMenuCog(bot))