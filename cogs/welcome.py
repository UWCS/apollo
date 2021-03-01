from datetime import datetime

from discord import Member
from discord.ext.commands import Bot, Cog
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy_utils import ScalarListException

from config import CONFIG
from models import db_session, User
from utils.welcome_messages import generate_welcome_message


class Welcome(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_member_join(self, member: Member):
        # Add the user to our database if they've never joined before
        user = db_session.query(User).filter(User.user_uid == member.id).first()
        if not user:
            user = User(user_uid=member.id, username=str(member))
            db_session.add(user)
        else:
            user.last_seen = datetime.utcnow()
        try:
            db_session.commit()
        except (ScalarListException, SQLAlchemyError):
            db_session.rollback()

        #  await member.send(WELCOME_MESSAGE.format(user_id=member.id))

        # Join message
        channel = self.bot.get_channel(CONFIG["UWCS_WELCOME_CHANNEL_ID"])
        target = self.bot.get_channel(CONFIG["UWCS_INTROS_CHANNEL_ID"])
        message = generate_welcome_message(member.display_name, target.mention)
        await channel.send(message)


def setup(bot: Bot):
    bot.add_cog(Welcome(bot))