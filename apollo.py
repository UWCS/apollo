from discord.ext.commands import Bot, when_mentioned_or
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import models
from config import CONFIG

engine = create_engine(CONFIG['DATABASE_CONNECTION'], echo=CONFIG['SQL_LOGGING'])
db_session = Session(bind=engine)

bot = Bot(command_prefix=when_mentioned_or('!'))

# TODO: Add help string

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

    user = db_session.query(models.User).filter(models.User.user_uid == message.author.id).first()
    if not user:
        user = models.User(user_uid=message.author.id,
                           username='{username}#{number}'.format(username=message.author.name,
                                                                 number=message.author.discriminator))
        db_session.add(user)

    # TODO: Add karma scanning

    await bot.process_commands(message)


def init_tables(db_engine):
    models.Base.metadata.create_all(db_engine)


if __name__ == '__main__':
    # Initialise the tables
    init_tables(engine)

    bot.run(CONFIG['DISCORD_TOKEN'])
