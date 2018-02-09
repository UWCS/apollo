from discord.ext.commands import Bot, when_mentioned_or

from commands.verify import verify
from config import CONFIG
from models import User, db_session, init_tables, engine

DESCRIPTION = """
Apollo is the Discord bot for the University of Warwick Computing Society, designed to augment the server with a number of utilities and website services.

To verify your account please set your Discord tag (name and 4 digit number e.g.: Foo#1337) in account settings on the UWCS website and then PM the bot your university number.
"""

bot = Bot(command_prefix=when_mentioned_or('!'), description=DESCRIPTION)


@bot.event
async def on_ready():
    if CONFIG['BOT_LOGGING']:
        # TODO: Write this to a logging file?
        print('Logged in as')
        print(str(bot.user))
        print('------')


@bot.event
async def on_message(message):
    # If the message is by a bot then ignore it
    if message.author.bot:
        return

    user = db_session.query(User).filter(User.user_uid == message.author.id).first()
    if not user:
        user = User(user_uid=message.author.id,
                    username='{username}#{number}'.format(username=message.author.name,
                                                          number=message.author.discriminator))
        db_session.add(user)
    else:
        user.last_seen = message.created_at
        db_session.commit()

    # TODO: Add karma scanning

    await bot.process_commands(message)


if __name__ == '__main__':
    # Initialise the tables
    init_tables(engine)

    bot.add_command(verify)
    bot.run(CONFIG['DISCORD_TOKEN'])
