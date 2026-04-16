import asyncio
import inspect
import io
import logging
import re
from typing import Any

from discord import (
    AllowedMentions,
    Embed,
    Emoji,
    File,
    HTTPException,
    Interaction,
    Message,
    MessageReference,
    PartialEmoji,
    Reaction,
    TextStyle,
    User,
    Webhook,
    WebhookMessage,
    ui,
)
from discord.utils import maybe_coroutine
from PIL import Image, ImageDraw, ImageFont

from utils import replace_external_emoji

from .typing import Callback, GuildChannelMessageable, ModalCtx

font: ImageFont.FreeTypeFont | None = None
subfont: ImageFont.FreeTypeFont | None = None

try:
    font = ImageFont.truetype(
        "resources/Montserrat-SemiBold.ttf", 90
    )
    subfont = ImageFont.truetype(
        "resources/Montserrat-Medium.ttf", 45
    )
except OSError:
    logging.warning("Error loading announcement title fonts")


async def generate_announcement(
    channel: GuildChannelMessageable,
    text: str,
    webhook: Webhook | None = None,
    username: str | None = None,
    avatar: str | None = None,
    allowed_mentions: AllowedMentions = AllowedMentions.none(),
) -> list[WebhookMessage | Message]:
    """Interprets actual announcement text into titles, images, etc."""
    lines: list[str] = text.split("\n")
    accumulated_lines: list[str] = []
    messages: list[WebhookMessage | Message] = []

    async def send(**kwargs: Any) -> None:
        """Send wrapper. Adds sent message to messages, and posts to webhook if possible"""
        if webhook is not None:
            kwargs = {
                "username": username,
                "avatar_url": avatar,
            } | kwargs  # Default name and avatar to func args, but allow overwrite in send args

            webhook_message: WebhookMessage = await webhook.send(
                wait=True, allowed_mentions=allowed_mentions, **kwargs
            )

            messages.append(webhook_message)
        else:
            message: Message = await channel.send(allowed_mentions=allowed_mentions, **kwargs)

            messages.append(message)

    async def send_lines() -> None:
        """Posts all of accumulated wrapper"""
        concat = "\n".join(accumulated_lines)
        try:
            await send(content=replace_external_emoji(channel.guild, concat))
        except HTTPException:
            pass
        accumulated_lines.clear()

    # Send each line
    for line in lines:
        # Find each type
        sub_group = subfont is not None and re.search(r"^## ?(.+)$", line)
        title_group = font is not None and re.search(r"^# ?(.+)$", line)
        img_group = re.search(r"^IMG (.+)$", line)
        break_group = re.search(r"^BREAK$", line)
        # Carry out any action
        if sub_group or title_group or img_group or break_group:
            # Send pending lines before special line
            if accumulated_lines:
                await send_lines()

            if sub_group:  # Subtitle
                await send(file=create_subtitle(sub_group.group(1)))
            elif title_group:  # Title
                await send(file=create_title(title_group.group(1)))
            elif img_group:  # Image
                await send(content=img_group.group(1))
            elif break_group:
                pass

        else:  # Is just text
            if line and line[0] == "#":
                line = f"**{line.strip('# ')}**"
            if (len(accumulated_lines) + len(line)) > 1900:
                await send_lines()
            accumulated_lines.append(line)

    # Post remaining message
    if accumulated_lines:
        await send_lines()
    return messages


def create_title(title: str) -> File:
    assert font is not None

    left, top, right, bottom = font.getbbox(title)
    width = int(right - left)
    height = int(bottom - top)

    width = max(width, 750)
    outline = 5
    img: Image.Image = Image.new("RGBA", [width + outline + 6, height + outline + 10])
    d = ImageDraw.Draw(img)

    d.text(
        (outline / 2 + 3, outline - 3),
        title,
        font=font,
        fill="#3D53FF",
        stroke_width=outline,
        stroke_fill="#36393F",
    )

    return to_file(img)


def create_subtitle(title: str) -> File:
    assert subfont is not None

    left, top, right, bottom = subfont.getbbox(title)
    width = int(right - left)
    height = int(bottom - top)

    width = max(width, 350)
    outline = 3
    img: Image.Image = Image.new("RGBA", (width * 2 + outline + 6, height + outline + 10))
    d = ImageDraw.Draw(img)

    d.text(
        (outline / 2 + 3, outline - 3),
        title,
        font=subfont,
        fill="#3D53FF",
        stroke_width=outline,
        stroke_fill="#36393F",
    )

    return to_file(img)


def to_file(img: Image.Image) -> File:
    with io.BytesIO() as img_bin:
        img.save(img_bin, "PNG")
        img_bin.seek(0)
        return File(fp=img_bin, filename="title.png")


# Confirm messages
async def confirmation(
    ctx: ModalCtx,
    title: str,
    body: str,
    reactions: list[str | Emoji | PartialEmoji],
    interact_func: Callback,
    timeout_func: Callback,
    timeout: int = 60,
    content: str = "",
    fields: list[dict[str, Any] | tuple[str, str]] | None = None,
) -> Any:
    """
    Posts an embed with the prompt.
    If the author reacts with one of given reactions before timeout, interact_func will be called.
    Otherwise on timeout, timeout_func will be called
    """
    kwargs: dict[Any, Any] = {}
    if title or body:
        embed = Embed(title=title, description=body)
        if fields:
            for f in fields:
                if isinstance(f, dict):
                    embed.add_field(**f)
                if isinstance(f, list) or isinstance(f, tuple):
                    name, value = f
                    embed.add_field(name=name, value=value, inline=False)
        kwargs["embed"] = embed
    if content:
        kwargs["content"] = content

    msg: Message = await ctx.reply(**kwargs)
    for em in reactions:
        await msg.add_reaction(em)

    try:
        def check(r: Reaction, u: User) -> bool:
            return (
                r.message.id == msg.id
                and u == ctx.message.author
                and r.emoji in reactions
            )

        r, _ = await ctx.bot.wait_for(
            "reaction_add",
            check=check,
            timeout=timeout,
        )
        return await pack_and_call(
            interact_func,
            m=msg,
            msg=msg,
            message=msg,
            r=r,
            react=r,
            reaction=r,
            emoji=r,
        )
    except TimeoutError:
        return await pack_and_call(timeout_func, m=msg, msg=msg, message=msg)


async def pack_and_call(f: Callback, **kwargs: Any) -> Any:
    """Matches args of the interact/timeout function to the ones given"""
    # Probably could replace with set params for interact function, but a little flexibility and overcomplication never hurt anyone, right?
    fkwargs = {}
    for fa in inspect.signature(f).parameters:
        fkwargs[fa] = kwargs[fa]
    return await maybe_coroutine(f, **fkwargs)


async def nothing(*_) -> None:
    pass


async def delete_msg(msg: Message) -> None:
    await msg.delete()


class ContentModal(ui.Modal, title="Content"):
    def __init__(self, placeholder: str) -> None:
        super().__init__()
        self.result = None
        self.done = asyncio.Event()

        self.content: ui.TextInput[Any] = ui.TextInput(
            label="Content", style=TextStyle.long, default=placeholder
        )
        self.add_item(self.content)

    async def on_submit(self, interaction: Interaction) -> None:
        self.result = self.content.value
        self.done.set()
        await interaction.response.send_message("Message Edited", ephemeral=True)

async def get_long_msg(ctx: ModalCtx, orig_content: str = "", placeholder: str = "") -> tuple[ModalCtx, str] | tuple[ModalCtx, str | None] | tuple[ModalCtx, None]:
    if orig_content != "":
        return ctx, orig_content

    ref: MessageReference | None = ctx.message.reference

    if ref is not None:  # If reply (for text cmd)
        assert ref.message_id is not None
        rep_msg = await ctx.channel.fetch_message(ref.message_id)
        return ctx, rep_msg.content

    elif ctx.interaction:  # If interaction (slash cmd)
        modal = ContentModal(placeholder)
        await ctx.interaction.response.send_modal(modal)
        await modal.done.wait()
        return ctx, modal.result

    return ctx, None
