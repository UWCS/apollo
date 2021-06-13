import configparser
import logging
import os
import re
import shutil
from pathlib import Path

import requests
from discord import Color, Embed
from discord.ext import commands
from discord.ext.commands import Bot, Context, check, clean_content
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy_utils import ScalarListException

from config import CONFIG
from models import FilamentType, db_session
from utils import get_name_string, is_compsoc_exec_in_guild

LONG_HELP_TEXT = """
Commands to help cost and request something is 3D printed on the UWCS 3D printer.
"""
ADDF_LONG_TEXT = """
Adds a filament type to the bot's database. Format is a name in quotes, a cost per kilo, and an image of the filament (attached to the message or linked). An example:

!printtools add_filament "<name>" <profile> [<image_url>]
"""
DELF_LONG_TEXT = """
Removes a filament type from the bot's database. Takes the full name of the filament in quotes.
"""

SHORT_HELP_TEXT = """Utilities to help you use the UWCS 3D printer"""
COST_HELP_TEXT = """Get a rough cost of the 3D object to be 3D printed"""
ADDF_HELP_TEXT = """Add a filament type to the bot's database"""
DELF_HELP_TEXT = """Remove a filament type from the bot's database"""
LIST_HELP_TEXT = (
    """Lists all of the available filament. Takes an optional list filter"""
)
INFO_HELP_TEXT = """Gives information about the chosen filament, given in quotes"""


def get_valid_filename(s):
    """
    Lifted from Django's text utils:
    https://github.com/django/django/blob/master/django/utils/text.py#L221-L231
    """
    s = str(s).strip().replace(" ", "_")
    return re.sub(r"(?u)[^-\w.]", "", s)


class PrintTools(commands.Cog, name="Print tools"):
    def __init__(self, bot: Bot):
        self.print_root_dir = CONFIG.PRINTER_FILE_ROOT
        self.print_images_dir = self.print_root_dir / "images"
        self.print_profiles_dir = self.print_root_dir / "profiles"

        print_profiles = [
            x for x in os.listdir(self.print_profiles_dir) if x.endswith(".ini")
        ]
        self.print_profiles = dict(
            [(x, Path(self.print_profiles_dir, x)) for x in print_profiles]
        )

        self.bot = bot

    @commands.group(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def printtools(self, ctx: Context):
        if not ctx.invoked_subcommand:
            await ctx.send("Subcommand not found")

    @printtools.command(help=ADDF_LONG_TEXT, brief=ADDF_HELP_TEXT)
    @check(is_compsoc_exec_in_guild)
    async def add_filament(self, ctx: Context, *args: clean_content):
        # Check we have the bare minumum number of args
        if len(args) < 2:
            await ctx.send(
                "I need at least a filament name in quotes and the associated print profile."
            )
            return

        # Make sure there are the right number of args for each input type
        if len(args) < 3 and not ctx.message.attachments:
            await ctx.send(
                "Please provide an image of the filament by an image link or attachment"
            )

        # Do a quick check the folder(s) exist and make them if not
        self.print_images_dir.mkdir(parents=True, exist_ok=True)

        filament_name, filament_profile = args[:2]
        # Verify that the filament type is an expected type
        if not FilamentType.verify_type(str(filament_profile)):
            await ctx.send(
                f'Print profile "{filament_profile}" is not a valid profile. Currently accepted profiles are: `filamentum`, `prusament`.'
            )

        image_file = Path(self.print_images_dir, get_valid_filename(filament_name))

        # Get the image and save it to the filesystem
        if ctx.message.attachments:
            # Take the first attachment and save it
            image_attachment = ctx.message.attachments[0]
            filename = str(image_file) + "." + image_attachment.filename.split(".")[-1]
            await image_attachment.save(filename)
        else:
            image_url = args[2]
            filename = str(image_file) + "." + str(image_url).split(".")[-1]
            # Save the file to disk
            r = requests.get(image_url, stream=True)
            if r.status_code == 200:
                with open(filename, "wb") as f:
                    r.raw.decode_content = True
                    shutil.copyfileobj(r.raw, f)

        # Save the model to the database
        filament = FilamentType(
            name=str(filament_name),
            profile=str(filament_profile).casefold(),
            image_path=str(image_file),
        )
        db_session.add(filament)
        try:
            db_session.commit()
            await ctx.send(f'"{filament_name}" added to the available filament list!')
        except (ScalarListException, SQLAlchemyError) as e:
            db_session.rollback()
            logging.exception(e)
            await ctx.send(f'Could not add "{filament_name}" due to an internal error.')

    @printtools.command(help=DELF_LONG_TEXT, brief=DELF_HELP_TEXT)
    @check(is_compsoc_exec_in_guild)
    async def del_filament(self, ctx: Context, filament_name: clean_content):
        filament = (
            db_session.query(FilamentType)
            .filter(FilamentType.name.like(filament_name))
            .first()
        )

        if not filament:
            await ctx.send(
                f'Couldn\'t find a filament that matches the name "{filament_name}"'
            )
            return

        db_session.delete(filament)
        try:
            db_session.commit()
            await ctx.send(f'Removed "{filament_name}" from the filament list!')
        except (ScalarListException, SQLAlchemyError) as e:
            db_session.rollback()
            logging.exception(e)
            await ctx.send(
                f'Could not remove "{filament_name}" due to an internal error.'
            )

    @printtools.command(name="list", help=LIST_HELP_TEXT, brief=LIST_HELP_TEXT)
    async def list_filament(self, ctx: Context, *filter: clean_content):
        # If there is a search filter then use it
        # TODO: Use the embeds for this
        if filter:
            filter_str = str(filter[0])
            filaments = (
                db_session.query(FilamentType)
                .filter(FilamentType.name.ilike(f"%{filter_str}%"))
                .order_by(FilamentType.name)
                .all()
            )
        else:
            filaments = db_session.query(FilamentType).order_by(FilamentType.name).all()

        if filaments:
            filament_list = []
            for f in filaments:
                # Format the list nicely
                config = configparser.ConfigParser()
                if self.print_profiles.get(f"uwcs_balanced_{f.profile}.ini", None):
                    config.read_file(
                        open(
                            self.print_profiles.get(f"uwcs_balanced_{f.profile}.ini"),
                            "r",
                        )
                    )
                    cost = f"- £{config.get('cfg', 'filament_cost')}/kg"
                else:
                    cost = "- Unknown cost"

                filament_list.append(f" • **{f.name}** {cost}")

            filament_list = "\n".join(filament_list)
            if len(filaments) > 1:
                await ctx.send(f"Our current filaments:\n{filament_list}")
            else:
                await ctx.send(f"Our current filament:\n{filament_list}")
        else:
            if filter:
                await ctx.send(f'There are no filaments that match "{str(filter[0])}"')
            else:
                await ctx.send("There are no filaments currently available")

    @printtools.command(help=INFO_HELP_TEXT, brief=INFO_HELP_TEXT)
    async def info(self, ctx: Context, filament_name: clean_content):
        filament = (
            db_session.query(FilamentType)
            .filter(FilamentType.name.like(filament_name))
            .first()
        )

        if not filament:
            await ctx.send(
                f'Couldn\'t find a filament that matches the name "{filament_name}"'
            )
            return

        # Construct the embed
        embed_colour = Color.from_rgb(61, 83, 255)
        embed_title = f'Filament info for "{filament_name}"'
        host = CONFIG.FIG_HOST_URL + "/filaments"
        image_file = filament.image_path.split("/")[-1]

        embed = Embed(title=embed_title, color=embed_colour)
        embed.add_field(name="Cost per kilogram", value="{0:.2f}".format(filament.cost))
        embed.set_image(url=f"{host}/{image_file}")

        display_name = get_name_string(ctx.message)
        await ctx.send(f"Here you go, {display_name}! :page_facing_up:", embed=embed)

    @printtools.command(help=COST_HELP_TEXT, brief=COST_HELP_TEXT)
    async def cost(self, ctx: Context, filament: clean_content):
        msg = ctx.message

        if msg.attachments:
            # TODO: Iterate over each attachment and process it (check if it's STL)
            pass
        else:
            # TODO: Check the message text to see if there's a thingiverse/myminifactory link
            # Any other link has to be done manually for sake of security
            pass

        pass


def setup(bot: Bot):
    bot.add_cog(PrintTools(bot))
