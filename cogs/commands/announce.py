import asyncio
import datetime
import logging

import discord
from discord import AllowedMentions, Interaction, ui
from discord.ext import commands
from discord.ext.commands import Bot, Context, MissingPermissions
from humanize import precisedelta
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy_utils import ScalarListException

import utils.utils
from config import CONFIG
from models import Announcement, db_session
from utils import (
    DateTimeConverter,
    get_database_user,
    get_name_string,
    is_compsoc_exec_in_guild,
    user_is_irc_bot,
)
from utils.announce_utils import generate_announcement


async def get_webhook(channel):
    """Finds announcement webhook, or creates it necessary"""
    try:
        # Find webhook
        webhooks = await channel.webhooks()
        webhook = next((w for w in webhooks if w.name == "Apollo Announcements"), None)
        if webhook is None:  # Create if not existing
            webhook = await channel.create_webhook(name="Apollo Announcements")
        return webhook
    except MissingPermissions:
        return None


class ContentButton(ui.Button):
    def __init__(self, channel: discord.TextChannel, trigger_time: datetime.datetime):
        super().__init__(
            label="Content Modal", emoji="📝", style=discord.ButtonStyle.grey
        )
        self.channel = channel
        self.trigger_time = trigger_time

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ContentModal())


class ContentModal(ui.Modal, title="Announcement Content"):
    def __init__(self, cog, ctx, channel, trigger_time):
        super().__init__()
        self.channel = channel
        self.trigger_time = trigger_time
        self.ctx = ctx
        self.cog = cog

    content = ui.TextInput(label="Content", style=discord.TextStyle.long)

    async def on_submit(self, interaction: discord.Interaction):
        # await interaction.response.send_message(f'Thanks for your response, {self.name}!', ephemeral=True)
        await self.cog.prev_and_add(
            self.ctx, self.channel, self.trigger_time, self.content.value
        )
        await interaction.response.send_message(
            f"Raw content:\n```{self.content.value}```"
        )


class Announcements(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.bot.loop.create_task(announcement_check(self.bot))

    @commands.hybrid_group()
    @commands.check(is_compsoc_exec_in_guild)
    async def announcement(self, ctx: Context):
        """
        Manage scheduled announcements
        """
        if not ctx.invoked_subcommand:
            await ctx.send("Subcommand not found.")

    @announcement.command()
    async def add(
        self,
        ctx: Context,
        channel: discord.TextChannel,
        trigger_time: DateTimeConverter,
        *,
        content: str = None,
    ):
        """
        Add an announcement for a scheduled time. **Reply to a message with the desired content**
        Ensure time is in quotation marks if multiple words, the announcement will the rest of discord message.
        """
        # Function very similar to reminders

        now = datetime.datetime.now() - datetime.timedelta(minutes=5)
        if not trigger_time:
            return await ctx.send("Incorrect time format, please see help text.")
        if trigger_time < now:
            return await ctx.send("That time is in the past.")

        ref = ctx.message.reference
        if content is None:
            if ref:
                rep_msg = await ctx.channel.fetch_message(ref.message_id)
                content = rep_msg.content
            else:
                if ctx.interaction:
                    await ctx.interaction.response.send_modal(
                        ContentModal(self, ctx, channel, trigger_time)
                    )
                    return
        await self.prev_and_add(ctx, channel, trigger_time, content)

    async def prev_and_add(self, ctx, channel, trigger_time, content):
        # Preview render of announcement. If menu's input confirms, continue
        await preview_announcement(
            ctx,
            content,
            False,
            bot=self.bot,
            add_args=[ctx, channel, trigger_time, content],
        )

    @announcement.command()
    async def preview(self, ctx: Context, *, announcement_content: str):
        """
        Preview the formatting of an announcement body
        """
        await preview_announcement(ctx, announcement_content, True, bot=self.bot)

    @announcement.command()
    async def list(self, ctx: Context):
        """
        List all upcoming announcements
        """
        # Find all upcoming announcements
        announcements = (
            db_session.query(Announcement)
            .filter(
                Announcement.trigger_at >= datetime.datetime.now(),
                Announcement.triggered == False,
            )
            .all()
        )

        msg_text = ["**Pending Announcements:**"]
        for a in announcements:
            id = a.id
            # Get author mention
            if a.irc_name:
                author_name = a.irc_name
            else:
                author_name = self.bot.get_user(a.user.user_uid).mention
            time = a.trigger_at
            loc = a.playback_channel_id
            preview = a.announcement_content.split("\n")[0]

            # Construct message
            msg_text.append(
                f"**{id}: in <#{loc}> <t:{int(time.timestamp())}:R> by {author_name}**\n\t{preview}\n"
            )

        # Send messages
        for text in utils.utils.split_into_messages(msg_text):
            await ctx.send(text, allowed_mentions=AllowedMentions.none())

    @announcement.command()
    async def cancel(self, ctx: Context, announcement_id: int):
        """
        Cancel an upcoming announcement.
        The announcement id can be found through `!announcement list`.
        """
        # Find result
        result = (
            db_session.query(Announcement)
            .where(Announcement.id == announcement_id)
            .first()
        )
        # Attempt to delete
        if result:
            db_session.delete(result)
            db_session.commit()
            await ctx.send("Announcement Deleted")
        else:
            await ctx.send("Announcement does not exist")

    @announcement.command()
    async def check(self, ctx: Context, announcement_id: int):
        """
        Check the raw source and preview of an upcoming announcement.
        The announcement id can be found through `!announcement list`.
        """
        # Find result
        result = (
            db_session.query(Announcement)
            .where(Announcement.id == announcement_id)
            .first()
        )
        # Post source and Render preview
        await ctx.send(f"**Message Source:**```\n{result.announcement_content}```")
        await preview_announcement(
            ctx, result.announcement_content, True, False, self.bot
        )

    @announcement.command()
    async def mention(self, ctx: Context, announcement_id: int, role: discord.Role):
        """
        Add a role mention to the end of the messsage.
        Use this command to avoid pinging roles when writing the message. Roles can be specified by name or id.
        """
        # Find result
        announcement = (
            db_session.query(Announcement)
            .where(Announcement.id == announcement_id)
            .first()
        )
        # Add pings to message
        announcement.announcement_content += "\n" + role.mention
        db_session.commit()

        await ctx.send(
            f"Pings added for {role.name} to announcement {announcement_id}."
        )


async def preview_announcement(
    ctx,
    announcement_content: str,
    preview: bool = True,
    menu: bool = True,
    bot=None,
    add_args=None,
):
    """Posts preview to command channel"""
    channel = ctx.channel
    webhook = await get_webhook(channel)

    messages = [await channel.send("**Announcement Preview:**")]
    author = ctx.author if CONFIG.ANNOUNCEMENT_IMPERSONATE else bot
    messages += await generate_announcement(
        channel, announcement_content, webhook, author.name, author.avatar.url
    )
    messages.append(await channel.send("**End of Announcement Preview**"))
    if menu:
        return await preview_edit_menu(
            ctx, messages, announcement_content, preview, add_args
        )


async def announcement_check(bot):
    """Checks for any announcements that need to be posted and haven't"""
    await bot.wait_until_ready()
    while not bot.is_closed():
        # Find announcements that need posting
        now = datetime.datetime.now()
        announcements = (
            db_session.query(Announcement)
            .filter(Announcement.trigger_at <= now, Announcement.triggered == False)
            .all()
        )

        for a in announcements:
            channel = bot.get_channel(a.playback_channel_id)
            webhook = await get_webhook(channel)

            # Find author info
            name, avatar = None, None
            if a.irc_name:
                name = a.irc_name
            else:
                author = (
                    bot.get_user(a.user.user_uid)
                    if CONFIG.ANNOUNCEMENT_IMPERSONATE
                    else bot.user
                )
                name, avatar = author.name, author.avatar.url

            message = a.announcement_content
            a.triggered = True
            db_session.commit()

            # Post message
            await generate_announcement(
                channel, message, webhook, name, avatar, AllowedMentions.all()
            )

        await asyncio.sleep(CONFIG.ANNOUNCEMENT_SEARCH_INTERVAL)


async def preview_edit_menu(
    ctx, messages, announcement_content, preview, add_args=None
):
    """Menu to post, edit or cancel preview"""
    msg = None

    class AcceptButton(ui.Button):
        def __init__(self):
            super().__init__(label="Accept", emoji="✅", style=discord.ButtonStyle.green)

        async def callback(self, interaction: Interaction):
            await msg.delete()
            for ann_msg in messages:
                await ann_msg.delete()
            if preview:
                await interaction.response.send_message(
                    f"Preview complete. Send this message with\n`!announcement add #announcements 10s \n{announcement_content}`"
                )
            else:
                await add_announcement(*add_args)

    class EditButton(ui.Button):
        def __init__(self):
            super().__init__(label="Edit", emoji="✏️", style=discord.ButtonStyle.grey)

        async def callback(self, interaction: Interaction):
            await msg.delete()
            for ann_msg in messages:
                await ann_msg.delete()
            if not ctx.interaction:
                await interaction.response.send_message("Refreshing...")
                edit_msg: discord.Message = await ctx.fetch_message(ctx.message.id)
                await ctx.bot.process_commands(edit_msg)
            else:
                await interaction.response.send_message(
                    "Slash command edit not supported"
                )

    class CancelButton(ui.Button):
        def __init__(self):
            super().__init__(label="Cancel", emoji="✖️", style=discord.ButtonStyle.red)

        async def callback(self, interaction: Interaction):
            await msg.delete()
            for ann_msg in messages:
                await ann_msg.delete()
            await interaction.response.send_message("Announcement cancelled")

    class ConfirmView(ui.View):
        def __init__(self):
            super().__init__()
            self.add_item(AcceptButton())
            self.add_item(EditButton())
            self.add_item(CancelButton())

        async def on_timeout(self):
            await msg.delete()
            await ctx.send(
                f"**Timeout.** Restart posting with: `!announcement preview {announcement_content}`"
            )
            for ann_msg in messages:
                try:
                    await ann_msg.delete()
                except discord.errors.NotFound:
                    pass

    msg = await ctx.send(
        "**Edit Preview**\nEdit source before edit", view=ConfirmView()
    )


async def add_announcement(ctx, channel, trigger_time, announcement_content):
    display_name = get_name_string(ctx.message)
    # Set the id to a random value if the author was the bridge bot, since we won't be using it anyway
    # if ctx.message.clean_content.startswith("**<"): <---- FOR TESTING
    if user_is_irc_bot(ctx):
        author_id = 1
        irc_n = display_name
    else:
        author_id = get_database_user(ctx.author).id
        irc_n = None

    new_announcement = Announcement(
        user_id=author_id,
        announcement_content=announcement_content,
        trigger_at=trigger_time,
        triggered=False,
        playback_channel_id=channel.id,
        irc_name=irc_n,
    )
    db_session.add(new_announcement)
    try:
        db_session.commit()
        gran = precisedelta(CONFIG.ANNOUNCEMENT_SEARCH_INTERVAL, minimum_unit="seconds")
        await ctx.send(
            f"Announcement prepared for <t:{int(trigger_time.timestamp())}:R> (granularity is {gran})."
        )

    except (ScalarListException, SQLAlchemyError) as e:
        db_session.rollback()
        logging.exception(e)
        await ctx.send(f"Something went wrong")


async def setup(bot: Bot):
    await bot.add_cog(Announcements(bot))
