import discord
from discord import AllowedMentions
from discord.ext import commands
from discord.ext.commands import Bot, Context
from discord.ui import Button, View
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from models import User, db_session
from models.role_menu import RoleEntry, RoleMenu
from utils import is_compsoc_exec_in_guild, rerun_to_confirm
from utils.announce_utils import get_long_msg


# Records last ephemeral message to each user, so can edit for future votes
class RoleButton(Button):
    def __init__(self, interface, role: discord.Role, emoji: str):
        super().__init__(label=role.name)
        self.role = role
        self.interface = interface

    async def callback(self, interaction: discord.Interaction):
        """Toggles user's role"""
        user = interaction.user
        if self.role not in user.roles:
            await user.add_roles(self.role, reason="Button Role")
            await interaction.response.send_message(
                f"Added role {self.role.mention}",
                allowed_mentions=AllowedMentions.none(),
                ephemeral=True,
            )
        else:
            await user.remove_roles(self.role, reason="Button Role")
            await interaction.response.send_message(
                f"Removed role {self.role.mention}",
                allowed_mentions=AllowedMentions.none(),
                ephemeral=True,
            )


class RoleMenuCog(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.view_records = {}
        self.delete_confirm = {}

    @commands.Cog.listener()
    async def on_ready(self):
        """When the bot starts, recreate all menus' buttons, so interactions will be picked up"""
        await self.bot.wait_until_ready()

        role_menus = db_session.query(RoleMenu).all()
        for menu in role_menus:
            guild = self.bot.get_guild(menu.guild_id)

            msg = await self.get_message_from_ids(
                menu.guild_id, menu.channel_id, menu.message_id
            )
            if msg is None:
                continue

            await msg.edit(view=self.recreate_view(menu.id, guild, msg))

    def recreate_view(self, mid, guild, msg):
        """Create buttons from DB entries for menu"""
        view = View()
        for entry in db_session.query(RoleEntry).filter(RoleEntry.menu_id == mid).all():
            view.add_item(RoleButton(self, guild.get_role(entry.role), em))
        self.view_records[msg.id] = view
        return view

    @commands.hybrid_group(help="Manage role menus, exec only")
    @commands.check(is_compsoc_exec_in_guild)
    async def roles(self, ctx: Context):
        if not ctx.invoked_subcommand:
            await ctx.send("Subcommand not found")

    @roles.command(
        brief="Create an empty role menu",
        help="Create an empty role menu. msg_ref must be unique.",
    )
    async def create(
        self,
        ctx: Context,
        msg_ref: str,
        title: str,
        channel: discord.TextChannel,
        description: str = None,
    ):
        msg = None
        try:  # Create fields and add to DB
            text = f"**{title}**"
            if description:
                text += f"\n{description}\n"
            msg = await channel.send(text)
            menu = RoleMenu(
                msg_ref=msg_ref,
                guild_id=ctx.guild.id,
                title=title,
                channel_id=channel.id,
                message_id=msg.id,
            )
            db_session.add(menu)
            db_session.commit()
            await ctx.send(f"Role Menu `{msg_ref}` created in {channel.mention}")

        except IntegrityError:
            db_session.rollback()
            await ctx.send(
                f"A Role Menu with reference `{msg_ref}` already exists in this server."
            )
        except SQLAlchemyError as e:
            print(e)
            db_session.rollback()
            await ctx.send("Database error creating menu")
            raise

    @roles.command(
        brief="Add a role to a role menu", help="Add a role to a particular role menu"
    )
    async def add(
        self, ctx, msg_ref, role: discord.Role, *, description=None, emoji: str = None
    ):
        message, menu = await self.get_message(ctx, msg_ref)
        if message is None:
            return await ctx.send("Message no longer exists")

        prompt_start = f"{emoji} for " if emoji else ""
        new_content = (
            f"{message.content}\n_ _\n{prompt_start}**{role.name}** {description or ''}"
        )
        view = self.view_records.get(message.id, View())
        view.add_item(RoleButton(self, role, emoji))

        try:
            entry = RoleEntry(
                menu_id=menu.id,
                role=role.id,
                title=role.name,
                description=description,
                emoji=str(emoji),
            )
            db_session.add(entry)
            db_session.commit()
        except SQLAlchemyError as e:
            print(e)
            db_session.rollback()
            await ctx.send("Database error creating menu")
            raise

        await message.edit(content=new_content, view=view)
        self.view_records[message.id] = view
        await ctx.send(f"Button for role {role.name} added to `{msg_ref}`")

    @roles.command(
        brief="Add blank text to a menu",
        help="Add blank text to the end of a menu's body. Use !set_msg to customize message further.",
    )
    async def add_text(self, ctx, msg_ref, *, text):
        message, menu = await self.get_message(ctx, msg_ref)
        if message is None:
            return await ctx.send("Message no longer exists")

        text = text.replace("\\n", "\n")
        new_content = f"{message.content}{text}"
        await message.edit(content=new_content)
        await ctx.send(f"Text added to `{msg_ref}`")

    @roles.command(
        brief="Rewrite the menu's message",
        help="Rewrite the menu's message. Use the slash command or reply for nice editor, or reply to a message with the content in already",
    )
    async def set_msg(self, ctx, msg_ref, *, content=None):
        message, menu = await self.get_message(ctx, msg_ref)
        if message is None:
            return await ctx.send("Message no longer exists")
        old_content = message.content

        _, content = await get_long_msg(ctx, content, message.content)

        await message.edit(content=content)
        await ctx.send(
            f"Set menu `{msg_ref}` text to:\n```{content}```\n**Old Content:**\n```{old_content}```"
        )

    @roles.command(
        brief="Remove a single role from a menu",
        help="Remove a single role from a particular menu",
    )
    async def remove(self, ctx, msg_ref, role: discord.Role):
        msg, menu = await self.get_message(ctx, msg_ref)
        if msg is None:
            return await ctx.send("Message no longer exists")

        entry = (
            db_session.query(RoleEntry)
            .filter(RoleEntry.menu_id == menu.id)
            .filter(RoleEntry.role == role.id)
            .one_or_none()
        )
        if entry is None:
            return await ctx.send(
                f"No role {role.mention} exists in menu {menu.msg_ref}"
            )
        try:
            db_session.delete(entry)
            db_session.commit()
        except SQLAlchemyError as e:
            print(e)
            db_session.rollback()
            return await ctx.send("Database error deleting role entry")

        guild = self.bot.get_guild(menu.guild_id)
        # Recreate view, as buttons change (and View.from_message doesn't keep hooks)
        view = self.recreate_view(menu.id, guild, msg)
        await msg.edit(view=view)

        await ctx.send(
            f"Deleted role {role} from menu `{msg_ref}`. Next, you should manually edit the message to remove the role, since this is dangerous to automate."
        )

    @roles.command(
        brief="Delets a full role menu",
        help="Deletes a full role menu. Will prompt you to re-run, just for a little security",
    )
    @rerun_to_confirm(
        key_name="msg_ref",
        confirm_msg="Warning, this will delete this role menu. Re-run to confirm.",
    )
    async def delete(self, ctx, msg_ref):
        message, menu = await self.get_message(ctx, msg_ref)
        if message is not None:
            try:
                await message.delete()
            except discord.errors.NotFound:
                pass
        try:
            db_session.delete(menu)
            db_session.commit()
        except SQLAlchemyError as e:
            print(e)
            db_session.rollback()
            await ctx.send("Database error deleting menu")
        await ctx.send(f"Deleted menu `{msg_ref}`")

    @roles.command()
    async def list(self, ctx):
        guild: discord.Guild = ctx.guild

        menus: RoleMenu = (
            db_session.query(RoleMenu).filter(RoleMenu.guild_id == guild.id).all()
        )

        msg = "**All Button Roles:**\n"
        msg += "\n".join(
            f"`{m.msg_ref}` **{m.title}** in {guild.get_channel(m.channel_id).mention}"
            for m in menus
        )
        await ctx.send(msg)

    def get_menu(self, guild_id, ref):
        """Finds message data for RR from ref"""
        return (
            db_session.query(RoleMenu)
            .filter(RoleMenu.msg_ref == ref)
            .filter(RoleMenu.guild_id == guild_id)
            .one_or_none()
        )

    async def get_message(self, ctx, msg_ref):
        # Fetch data
        guild: discord.Guild = ctx.guild
        menu = self.get_menu(guild.id, msg_ref)
        if not menu:
            raise Exception(f"No message exists with reference `{msg_ref}`.")

        # Edit embed to include new option
        try:
            channel = guild.get_channel(menu.channel_id)
            msg = await channel.fetch_message(menu.message_id)
        except discord.errors.NotFound as e:
            return None, menu
        return msg, menu

    async def get_message_from_ids(self, gid, cid, mid):
        # Edit embed to include new option
        try:
            guild = self.bot.get_guild(gid)
            channel = guild.get_channel(cid)
            msg = await channel.fetch_message(mid)
        except discord.errors.NotFound as e:
            return None
        return msg


async def setup(bot: Bot):
    await bot.add_cog(RoleMenuCog(bot))
