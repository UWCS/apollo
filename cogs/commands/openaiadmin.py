from discord import User
from discord.ext import commands
from discord.ext.commands import Bot, Context, check

from models import db_session
from models.openai import OpenAI
from utils import get_database_user, is_compsoc_exec_in_guild, is_user_banned_openAI

LONG_HELP_TEXT = """
Exec-only command to stop or reallow a user from usinf openAI functionality in apollo (Dalle and ChatGPT)
"""


class OpenAIAdmin(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief="ban/unban user from openAI")
    @check(is_compsoc_exec_in_guild)
    async def openaiban(self, ctx: Context, user: User, ban: bool):
        """bans or unbans a user from openAI commands"""

        if user == ctx.author:
            return await ctx.reply("You can't ban yourself")

        db_user = get_database_user(user)

        if not db_user:
            return await ctx.reply("User not found please try again")

        is_banned = (  # a user is banned if in the db
            db_session.query(OpenAI).filter(OpenAI.user_id == db_user.id).count() == 1
        )
        if ban:
            if is_banned:
                return await ctx.reply("User already banned")

            banned_user = OpenAI(user_id=db_user.id)
            db_session.add(banned_user)
        else:
            if not is_banned:
                return await ctx.reply("User not banned")

            db_session.query(OpenAI).filter(OpenAI.user_id == db_user.id).delete()

        db_session.commit()
        await ctx.reply(
            f"User {user} has been {'banned' if ban else 'unbanned'} from openAI commands"
        )

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief="list banned users")
    @check(is_compsoc_exec_in_guild)
    async def openaibanlist(self, ctx: Context):
        """lists all users banned from openAI commands"""
        banned_users = db_session.query(OpenAI).all()  # get all users in db
        if not banned_users:
            return await ctx.reply("No users banned")

        banned_users = "\n".join(  # make list of names
            [self.bot.get_user(user.user_id).name for user in banned_users]
        )
        await ctx.reply(f"Users banned from openAI:\n{banned_users}")

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief="is user banned")
    async def openaiisbanned(self, ctx: Context, user: User):
        """checks if user is banned from openAI commands"""
        is_banned = is_user_banned_openAI(user)
        await ctx.reply(
            f"User {user} is {'banned' if is_banned else 'not banned'} from using openAI commands"
        )


async def setup(bot: Bot):
    await bot.add_cog(OpenAIAdmin(bot))
