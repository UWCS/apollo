import logging
from datetime import datetime
from pathlib import Path
from random import choice, choices

import yaml
from discord import Member
from discord.ext.commands import Bot, Cog
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy_utils import ScalarListException

from config import CONFIG
from models import User, db_session
from utils import get_database_user


class Category:
    """Categories of favourite things."""

    def __init__(self, cat: dict):
        self.name = cat.get("name")
        self.template = cat.get("template", "{}")
        self.values = cat.get("values", [])
        self.weight = cat.get("weight")
        if self.weight is None or self.weight == "LENGTH":
            self.weight = len(self.values)

    def generate(self):
        return self.template.format(choice(self.values))


class Welcome(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        with open(Path("resources", "welcome_messages.yaml")) as f:
            parsed = yaml.full_load(f).get("welcome_messages")
        self.greetings = parsed.get("greetings")
        self.categories = [Category(c) for c in parsed.get("categories")]
        self.category_weights = [c.weight for c in self.categories]
        self.welcome_template = parsed.get("message")
        self.roles_id = parsed.get("roles-channel-id")

    def generate_welcome_message(self, name):
        greeting = choice(self.greetings)
        category = choices(self.categories, self.category_weights)[0]
        roles_channel = self.bot.get_channel(CONFIG.UWCS_ROLES_CHANNEL_ID).mention
        thing = category.generate()
        return self.welcome_template.format(
            greetings=greeting, name=name, roles_channel=roles_channel, thing=thing
        )

    @Cog.listener()
    async def on_member_join(self, member: Member):
        """Add the user to our database if they've never joined before"""
        user = get_database_user(member)
        if not user:
            user = User(user_uid=member.id, username=str(member))
            db_session.add(user)
        else:
            user.last_seen = datetime.utcnow()
        try:
            db_session.commit()
        except (ScalarListException, SQLAlchemyError) as e:
            logging.exception(e)
            db_session.rollback()

        # Send welcome on join, if membership verification is not enabled
        if "MEMBER_VERIFICATION_GATE_ENABLED" not in member.guild.features:
            channel = self.bot.get_channel(CONFIG.UWCS_WELCOME_CHANNEL_ID)
            await channel.send(self.generate_welcome_message(member.display_name))

    @Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        """Send a welcome message to members after they clear the welcome and membership screening screens."""
        if not before.pending or after.pending:
            return
        channel = self.bot.get_channel(CONFIG.UWCS_WELCOME_CHANNEL_ID)
        await channel.send(self.generate_welcome_message(after.display_name))


def setup(bot: Bot):
    bot.add_cog(Welcome(bot))
