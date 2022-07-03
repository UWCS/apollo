import inspect
import re

from discord.ext.commands import Context

import utils
import discord
from PIL import Image, ImageFont, ImageDraw
import io

font: ImageFont.ImageFont = ImageFont.truetype("resources/Montserrat-SemiBold.ttf", 90)
subfont: ImageFont.ImageFont = ImageFont.truetype("resources/Montserrat-Medium.ttf", 45)


async def generate_announcement(channel, text, webhook=None, username=None, avatar=None):
    lines = text.split("\n")
    accumulated_lines = []
    messages = []

    if webhook is None: print("No webhook exists")

    # Wrappers for adding message to messages after sending
    async def send(**kwargs):
        if webhook is not None:
            kwargs = {"username": username, "avatar_url": avatar, "wait": True} | kwargs  # Default name and avatar to func args, but allow overwrite in send args
            messages.append(await webhook.send(**kwargs))
        else:
            messages.append(await channel.send(**kwargs))

    async def send_lines():
        concat = "\n".join(accumulated_lines)
        try: await send(content=utils.replace_external_emoji(channel.guild, concat))
        except discord.HTTPException: pass
        accumulated_lines.clear()

    # Send each line
    for line in lines:
        # Find each type
        sub_group = re.search(r"^## ?(.+)$", line)
        title_group = re.search(r"^# ?(.+)$", line)
        img_group = re.search(r"^IMG (.+)$", line)
        break_group = re.search(r"^BREAK$", line)
        # Empty out any lines
        if sub_group or title_group or img_group or break_group:
            if accumulated_lines: await send_lines()

            if sub_group:  # Subtitle
                await send(file=create_subtitle(sub_group.group(1)))
            elif title_group:  # Title
                await send(file=create_title(title_group.group(1)))
            elif img_group:  # Image
                await send(content=img_group.group(1))
            elif break_group:
                pass

        else:  # Is just text
            if (len(accumulated_lines) + len(line)) > 1900: await send_lines()
            accumulated_lines.append(line)

    # Post remaining message
    if accumulated_lines: await send_lines()
    return messages


def create_title(title):
    w, h = font.getsize(title)
    w = max(w, 750)
    outline = 5
    img: Image.Image = Image.new('RGBA', (w + outline + 6, h + outline + 10))
    d = ImageDraw.Draw(img)

    d.text((outline / 2 + 3, outline - 3), title, font=font, fill="#3D53FF", stroke_width=outline,
           stroke_fill="#36393F")

    return to_file(img)


def create_subtitle(title):
    w, h = subfont.getsize(title)
    w = max(w, 350)
    outline = 3
    img: Image.Image = Image.new('RGBA', (w * 2 + outline + 6, h + outline + 10))
    d = ImageDraw.Draw(img)

    d.text((outline / 2 + 3, outline - 3), title, font=subfont, fill="#3D53FF", stroke_width=outline,
           stroke_fill="#36393F")

    return to_file(img)

def to_file(img):
    with io.BytesIO() as img_bin:
        img.save(img_bin, 'PNG')
        img_bin.seek(0)
        return discord.File(fp=img_bin, filename='title.png')


# Confirm messages
async def confirmation(ctx: Context, title: str, body: str, reactions, interact_func, timeout_func, timeout=60, content="", fields=None):
    """
    Posts an embed with the prompt.
    If the author reacts with one of given reactions before timeout, interact_func will be called.
    Otherwise, timeout_func will be called
    """
    kwargs = {}
    if title or body:
        embed = discord.Embed(title=title, description=body)
        if fields:
            for f in fields:
                if isinstance(f, dict): embed.add_field(**f)
                if isinstance(f, list) or isinstance(f, tuple): embed.add_field(name=f[0], value=f[1], inline=False)
        kwargs["embed"] = embed
    if content: kwargs["content"] = content

    msg: discord.Message = await ctx.send(**kwargs)
    for em in reactions:
        await msg.add_reaction(em)

    try:
        r, _ = await ctx.bot.wait_for("reaction_add",
                      check=lambda r, u: r.message.id == msg.id and u == ctx.message.author and str(r.emoji) in reactions,
                      timeout=timeout)
        return await pack_and_call(interact_func, m=msg, msg=msg, message=msg, r=r, react=r, reaction=r, emoji=r)
    except TimeoutError:
        return await pack_and_call(timeout_func, m=msg, msg=msg, message=msg)


async def pack_and_call(f, **kwargs):
    """Matches args of the interact/timeout function to the ones given"""
    fkwargs = {}
    for fa in inspect.signature(f).parameters:
            fkwargs[fa] = kwargs[fa]
    return await discord.utils.maybe_coroutine(f, **fkwargs)


async def nothing(*args):
    pass


async def delete_msg(msg: discord.Message):
    await msg.delete()