from discord import User
from discord.ext import commands
from discord.ext.commands import Bot, Context

from models import db_session
from models.openai import OpenAI
from utils import get_database_user, is_compsoc_exec_in_guild

LONG_HELP_TEXT = """
Exec-only command to stop or reallow a user from usinf openAI functionality in apollo (Dalle and ChatGPT)
"""


class OpenAIAdmin(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief="ban/unban user from openAI")
    @check(is_compsoc_exec_in_guild)
    async def OpenAIBan(self, ctx: Context, user: User, ban: bool):
        if user == ctx.author:
            return await ctx.reply("You can't ban yourself")

        db_user = get_database_user(user)

        if db_user:
            return await ctx.reply("User not found please try again")

        is_banned = (
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
    async def OpenAIList(self, ctx: Context):
        banned_users = db_session.query(OpenAI).all()
        if not banned_users:
            return await ctx.reply("No users banned")

        banned_users = "\n".join(
            [self.bot.get_user(user.user_id).name for user in banned_users]
        )
        await ctx.reply(f"Users banned from openAI:\n{banned_users}")

    @commands.hybrid_command(help=LONG_HELP_TEXT, brief="is user banned")
    async def OpenAIIsBanned(self, ctx: Context, user: User):
        is_banned = await self.is_user_banned(user)
        await ctx.reply(
            f"User {user} is {'banned' if is_banned else 'not banned'} from using openAI commands"
        )

    async def is_user_banned(self, user: User):
        db_user = get_database_user(user)
        if not db_user:
            return false
        return (
            db_session.query(OpenAI).filter(OpenAI.user_id == db_user.id).count() == 1
        )


async def setup(bot: Bot):
    await bot.add_cog(OpenAIAdmin(bot))
