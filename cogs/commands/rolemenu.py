from typing import List, NamedTuple

import discord
from discord.ext import commands
from discord import AllowedMentions, ButtonStyle, InteractionMessage, Role
from discord.ext.commands import Context, Bot
from discord.ui import Button, View
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from models import User, db_session
from models.role_menu import RoleMenu, RoleEntry
from utils.announce_utils import get_long_msg

# Records last ephemeral message to each user, so can edit for future votes
class RoleButton(Button):
    def __init__(self, interface, role: discord.Role, emoji: str):
        super().__init__(label=role.name)
        self.role = role
        self.interface = interface

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        if self.role not in user.roles: 
            await user.add_roles(self.role, reason="Button Role")
            await interaction.response.send_message(f"Added role {self.role.mention}", allowed_mentions=AllowedMentions.none(), ephemeral=True)
        else: 
            await user.remove_roles(self.role, reason="Button Role")
            await interaction.response.send_message(f"Removed role {self.role.mention}", allowed_mentions=AllowedMentions.none(), ephemeral=True)


class RoleMenuCog(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.view_records = {}

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()

        role_menus = db_session.query(RoleMenu).all()
        for menu in role_menus:
            guild = self.bot.get_guild(menu.guild_id)
            
            try:
                msg = await self.get_message_from_ids(menu.guild_id, menu.channel_id, menu.message_id)
            except discord.errors.NotFound:
                continue

            view = View()
            for entry in db_session.query(RoleEntry).filter(RoleEntry.menu_id == menu.id).all():
                print(entry)
                print(em := discord.PartialEmoji.from_str(entry.emoji))
                view.add_item(RoleButton(self, guild.get_role(entry.role), em))
            self.view_records[msg.id] = view
            await msg.edit(view=view)

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
    async def add(self, ctx, msg_ref, role: discord.Role, *, description=None, emoji: str=None):
        message, menu = await self.get_message(ctx, msg_ref)

        prompt_start = f"{emoji} for " if emoji else ""
        new_content = f"{message.content}\n_ _\n{prompt_start}**{role.name}** {description or ''}"
        view = self.view_records[message.id]
        view.add_item(RoleButton(self, role, emoji))

        try:
            entry = RoleEntry(menu_id=menu.id, role=role.id, title=role.name, description=description, emoji=str(emoji))
            db_session.add(entry)
            db_session.commit()
        except SQLAlchemyError:
            db_session.rollback()
            await ctx.send("Database error creating menu")
            raise

        await message.edit(content=new_content, view=view)
        self.view_records[message.id] = view
        await ctx.send(f"Button for role {role.name} added to `{msg_ref}`")

    @roles.command()
    async def add_text(self, ctx, msg_ref, *, text):
        message, menu = await self.get_message(ctx, msg_ref)

        text = text.replace("\\n", "\n")
        new_content = f"{message.content}{text}"
        await message.edit(content=new_content)
        await ctx.send(f"Text added to `{msg_ref}`")

    @roles.command()
    async def set_msg(self, ctx, msg_ref, *, content=None):
        message, menu = await self.get_message(ctx, msg_ref)

        _, content = await get_long_msg(ctx, content, message.content)
        
        await message.edit(content=content)
        await ctx.send(f"Set menu `{msg_ref}` text to:\n```{content}```")


    def get_menu(self, guild_id, ref):
        """Finds message data for RR from ref"""
        return (db_session.query(RoleMenu)
            .filter(RoleMenu.msg_ref == ref)
            .filter(RoleMenu.guild_id == guild_id)
            .one_or_none())

    async def get_message(self, ctx, msg_ref):
        # Fetch data
        guild: discord.Guild = ctx.guild
        menu = self.get_menu(guild.id, msg_ref)
        if not menu: raise Exception(f"No message exists with reference `{msg_ref}`.")

        # Edit embed to include new option
        channel = guild.get_channel(menu.channel_id)
        msg = await channel.fetch_message(menu.message_id)
        return msg, menu

    async def get_message_from_ids(self, gid, cid, mid):
        # Edit embed to include new option
        guild = self.bot.get_guild(gid)
        channel = guild.get_channel(cid)
        msg = await channel.fetch_message(mid)
        return msg


async def setup(bot: Bot):
    await bot.add_cog(RoleMenuCog(bot))