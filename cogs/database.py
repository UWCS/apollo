import logging
from datetime import datetime

from discord import Message
from discord.abc import GuildChannel
from discord.ext.commands import Bot, Cog, Context
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy_utils import ScalarListException

from config import CONFIG
from karma.karma import process_karma
from models import IgnoredChannel, LoggedMessage, MessageDiff, User, db_session
from utils import get_database_user, is_compsoc_exec_in_guild, user_is_irc_bot


async def not_in_blacklisted_channel(ctx: Context):
    return (
        await is_compsoc_exec_in_guild(ctx)
        or db_session.query(IgnoredChannel)
        .filter(IgnoredChannel.channel == ctx.channel.id)
        .first()
        is None
    )


class Database(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        # Set up a global check that we're not in a blacklisted channel
        self.bot.add_check(not_in_blacklisted_channel)

    @Cog.listener()
    async def on_message(self, message: Message):
        # If the message is by a bot that's not irc then ignore it
        if message.author.bot and not user_is_irc_bot(message):
            return

        user = get_database_user(message.author)
        if not user:
            user = User(user_uid=message.author.id, username=str(message.author))
            db_session.add(user)
        else:
            user.last_seen = message.created_at
        # Commit the session so the user is available now
        try:
            db_session.commit()
        except (ScalarListException, SQLAlchemyError) as e:
            db_session.rollback()
            logging.exception(e)
            # Something very wrong, but not way to reliably recover so abort
            return

        # Only log messages that were in a public channel
        if isinstance(message.channel, GuildChannel):
            # Log the message to the database
            logged_message = LoggedMessage(
                message_uid=message.id,
                message_content=message.clean_content,
                author=user.id,
                created_at=message.created_at,
                channel_name=message.channel.name,
            )
            db_session.add(logged_message)
            try:
                db_session.commit()
            except (ScalarListException, SQLAlchemyError) as e:
                db_session.rollback()
                logging.exception(e)
                return

            # KARMA

            # Get all specified command prefixes for the bot
            command_prefixes = self.bot.command_prefix(self.bot, message)
            # Only process karma if the message was not a command (ie did not start with a command prefix)
            if not any(
                message.content.startswith(prefix) for prefix in command_prefixes
            ):
                reply = process_karma(
                    message, logged_message.id, db_session, CONFIG.KARMA_TIMEOUT
                )
                if reply:
                    await message.channel.send(reply)

    @Cog.listener()
    async def on_message_edit(self, before: Message, after: Message):
        # Only care about messages that are in public channels
        if isinstance(before.channel, GuildChannel):
            # Message wasn't pinned
            if before.pinned == after.pinned:
                # Log any edits to messages
                original_message = (
                    db_session.query(LoggedMessage)
                    .filter(LoggedMessage.message_uid == before.id)
                    .first()
                )
                if original_message:
                    message_diff = MessageDiff(
                        original_message=original_message.id,
                        new_content=after.clean_content,
                        created_at=(after.edited_at or datetime.utcnow()),
                    )
                    db_session.add(message_diff)
                    try:
                        db_session.commit()
                    except (ScalarListException, SQLAlchemyError) as e:
                        db_session.rollback()
                        logging.exception(e)

    @Cog.listener()
    async def on_message_delete(self, message: Message):
        # Get the message from the database
        db_message = (
            db_session.query(LoggedMessage)
            .filter(LoggedMessage.message_uid == message.id)
            .one_or_none()
        )

        # Can't really do anything if the message isn't in the logs so only handle when it is
        if db_message:
            # Update the message deleted_at and commit the changes made
            db_message.deleted_at = datetime.utcnow()
            try:
                db_session.commit()
            except (ScalarListException, SQLAlchemyError) as e:
                db_session.rollback()
                logging.exception(e)


def setup(bot: Bot):
    bot.add_cog(Database(bot))
