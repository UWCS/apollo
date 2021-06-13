import logging
import re
from datetime import datetime

import requests
from discord.abc import PrivateChannel
from discord.ext import commands
from discord.ext.commands import Bot, CommandError, Context, check
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy_utils import ScalarListException

from config import CONFIG
from models import db_session
from utils import get_database_user, get_name_string

LONG_HELP_TEXT = """
Allows you to verify your account with your university number to gain the 'CompSoc Member' role. Should be sent in a private message.
"""

SHORT_HELP_TEXT = """PM the bot your university number to verify your account."""


class VerifyError(CommandError):
    message = None

    def __init__(self, message=None, *args):
        self.message = message
        super().__init__(*args)


def is_private_channel():
    async def predicate(ctx: Context):
        if not isinstance(ctx.channel, PrivateChannel):
            display_name = get_name_string(ctx.message)
            await ctx.message.delete()
            raise VerifyError(
                message=f"That command is supposed to be sent to me in a private message, {display_name}."
            )
        else:
            return True

    return check(predicate)


class Verify(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(ignore_extra=True, help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    @is_private_channel()
    async def verify(self, ctx: Context, uni_number: str):
        # Check that the university number provided is actually formatted correctly
        uni_id_regex = re.compile(r"[0-9]{7}")
        if not re.match(uni_id_regex, uni_number):
            raise VerifyError(
                message="'{id}' is not a valid university number.".format(id=uni_number)
            )

        # Get the discord data from our servers
        headers = {"Authorization": "Token {token}".format(token=CONFIG.UWCS_API_TOKEN)}
        api_request = requests.get(
            "https://uwcs.co.uk/api/user/{uni_id}/".format(uni_id=uni_number),
            headers=headers,
        )

        # If the request goes okay
        if api_request.status_code == 200:
            api_username = api_request.json()["discord_user"]
            if not api_username:
                # Tell the user they haven't set their discord tag on the website
                raise VerifyError(
                    message="Your Discord tag has not been set on the UWCS website - it can be set under your account "
                    "settings: https://uwcs.co.uk/accounts/profile/update/"
                )
            else:
                # This *shouldn't* happen but in the small case it may, just get the user to try again. Yay async systems!
                user = get_database_user(ctx.author)
                if not user:
                    raise VerifyError(
                        message="We've hit a snag verifying your account - please try again in a few minutes!"
                    )

                # Check if the user has already verified
                if user.uni_id == uni_number:
                    raise VerifyError(
                        message="You have already verified this university number."
                    )

                # Check they are who they say they are
                if not api_username == str(ctx.message.author):
                    raise VerifyError(
                        message="The user you're trying to verify doesn't match the tag associated with your university "
                        "ID - please make sure you've set your tag correctly and try again."
                    )

                # Get all of the objects necessary to apply the roles
                compsoc_guild = [
                    guild
                    for guild in ctx.bot.guilds
                    if guild.id == CONFIG.UWCS_DISCORD_ID
                ][0]
                compsoc_member = compsoc_guild.get_member(ctx.message.author.id)
                if not compsoc_member:
                    raise VerifyError(
                        message="It seems like you're not a member of the UWCS Discord yet. You can join us here: "
                        "https://discord.gg/uwcs"
                    )
                try:
                    compsoc_role = [
                        role
                        for role in compsoc_guild.roles
                        if role.id == CONFIG.UWCS_MEMBER_ROLE_ID
                    ][0]
                except IndexError:
                    raise VerifyError(
                        message="I can't find the role to give you on the UWCS Discord. Let one of the exec or admins "
                        "know so they can fix this problem!"
                    )

                # Give them the role and let them know
                await compsoc_member.add_roles(
                    compsoc_role,
                    reason="User verified with the university number of {uni_id}".format(
                        uni_id=uni_number
                    ),
                )
                user.uni_id = uni_number
                user.verified_at = datetime.utcnow()
                try:
                    db_session.commit()
                    await ctx.send(
                        "You're all verified and ready to go! Welcome to the UWCS Discord."
                    )
                except (ScalarListException, SQLAlchemyError) as e:
                    db_session.rollback()
                    logging.exception(e)
                    await ctx.send("Could not verify you due to an internal error.")

        else:
            raise VerifyError(
                message="That university number appears to be inactive or not exist - if you have just purchased "
                "membership please give the system 5 minutes to create an account. If you're not a member of the "
                "society you can purchase membership through the University of Warwick Student's union."
            )

    @verify.error
    async def verify_error_handler(self, ctx: Context, error: VerifyError):
        await ctx.send(error.message)


def setup(bot: Bot):
    bot.add_cog(Verify(bot))
