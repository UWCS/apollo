from datetime import datetime

from discord import Message, Member
from discord.abc import GuildChannel
from discord.ext.commands import Bot, when_mentioned_or

from config import CONFIG
from karma.karma import process_karma
from models import User, db_session, LoggedMessage, MessageDiff

DESCRIPTION = """
Apollo is the Discord bot for the University of Warwick Computing Society, designed to augment the server with a number of utilities and website services.

To verify your account please set your Discord tag (name and 4 digit number e.g.: Foo#1337) in account settings on the UWCS website and then PM the bot your university number.
"""
WELCOME_MESSAGE = """
Hey <@{user_id}>!

I'm Apollo, the UWCS Discord's friendly bot. I'd like to welcome you to the University of Warwick Computing Society Discord server!

If you are a member of the society then you can verify your account using the 'verify' command (use `!help verify` to find out more)! If you're not a member, you can join through the Warwick student's union website.

GLHF! :rocket:
"""

# The command extensions to be loaded by the bot
EXTENSIONS = ['commands.verify', 'commands.karma','commands.say']

bot = Bot(command_prefix=when_mentioned_or('!'), description=DESCRIPTION)


@bot.event
async def on_ready():
    if CONFIG['BOT_LOGGING']:
        # TODO: Write this to a logging file?
        print('Logged in as')
        print(str(bot.user))
        print('------')


@bot.event
async def on_message(message: Message):
    # If the message is by a bot then ignore it
    if message.author.bot and message.author.id != CONFIG['UWCS_DISCORD_BRIDGE_BOT_ID']:
        return

    user = db_session.query(User).filter(User.user_uid == message.author.id).first()
    if not user:
        user = User(user_uid=message.author.id, username=str(message.author))
        db_session.add(user)
    else:
        user.last_seen = message.created_at
    # Commit the session so the user is available now
    db_session.commit()

    # Only log messages that were in a public channel
    if isinstance(message.channel, GuildChannel):
        # Log the message to the database
        logged_message = LoggedMessage(message_uid=message.id, message_content=message.clean_content, author=user.id,
                                       created_at=message.created_at, channel_name=message.channel.name)
        db_session.add(logged_message)
        db_session.commit()

        # Get all specified command prefixes for the bot
        command_prefixes = bot.command_prefix(bot,message)
        # Only process karma if the message was not a command (ie did not start with a command prefix)
        if not True in [message.content.startswith(prefix) for prefix in command_prefixes]:
            reply = process_karma(message, logged_message.id, db_session, CONFIG['KARMA_TIMEOUT'])
            if reply:
                await message.channel.send(reply)

    await bot.process_commands(message)


@bot.event
async def on_message_edit(before: Message, after: Message):
    # Only care about messages that are in public channels
    if isinstance(before.channel, GuildChannel):
        # Message wasn't pinned
        if before.pinned == after.pinned:
            # Log any edits to messages
            original_message = db_session.query(LoggedMessage).filter(LoggedMessage.message_uid == before.id).first()
            if original_message:
                message_diff = MessageDiff(original_message=original_message.id, new_content=after.clean_content,
                                           created_at=(after.edited_at or datetime.utcnow()))
                db_session.add(message_diff)
                db_session.commit()


@bot.event
async def on_message_delete(message: Message):
    # Get the message from the database
    db_message = db_session.query(LoggedMessage).filter(LoggedMessage.message_uid == message.id).one_or_none()

    # Can't really do anything if the message isn't in the logs so only handle when it is
    if db_message:
        # Update the message deleted_at and commit the changes made
        db_message.deleted_at = datetime.utcnow()
        db_session.commit()

@bot.event
async def on_member_join(member: Member):
    # Add the user to our database if they've never joined before
    user = db_session.query(User).filter(User.user_uid == member.id).first()
    if not user:
        user = User(user_uid=member.id, username=str(member))
        db_session.add(user)
    else:
        user.last_seen = datetime.utcnow()
    db_session.commit()

    await member.send(WELCOME_MESSAGE.format(user_id=member.id))


if __name__ == '__main__':
    for extension in EXTENSIONS:
        try:
            bot.load_extension(extension)
        except Exception as e:
            exc = '{}: {}'.format(type(e).__name__, e)
            print('Failed to load extension {}\n{}'.format(extension, exc))

    bot.run(CONFIG['DISCORD_TOKEN'])
