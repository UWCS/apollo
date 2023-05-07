# Documentation

## General Structure

- `cogs/commands`: Where the main code for commands reside.
- `config`: Config parser.
- `migrations`: Handles database upgrades.
- `models`: Database ORM classes to map between Python and SQL.
- `tests`: Unit tests for some commands, still very WIP.
- `utils`: Some general shared utility functions.
- `karma`, `roll`, `printer`, `voting`: commands that have enough code to warrant a separate directory.
- `resources`: static resources and files used by Apollo

### Cogs

Cogs are how Discord.py organizes commands, each file is a separate cog with separate functionality. If you don't know about cogs already, ask on Discord or go [some d.py docs](https://discordpy.readthedocs.io/en/stable/ext/commands/cogs.html). If you want to temporarily disable a Cog, comment out its line in `apollo.py` while developing.

- cogs.welcome
- cogs.irc
- cogs.database
- cogs.parallelism
- cogs.channel_checker
- cogs.commands.admin
- cogs.commands.blacklist
- cogs.commands.counting
- cogs.commands.date
- cogs.commands.event_sync
- cogs.commands.flip
- cogs.commands.karma
- cogs.commands.lcalc
- cogs.commands.misc
- cogs.commands.quotes
- cogs.commands.rolemenu
- cogs.commands.reminders
- cogs.commands.announce
- cogs.commands.roll
- cogs.commands.roomsearch
- cogs.commands.say
- cogs.commands.tex
- cogs.commands.vote
- cogs.commands.widen

## Contributing

### Contributor Notes

- TODO Update

- When writing anything that needs to reply to a specific username, please do `from utils import get_name_string` and get the display string using this function, with the discord `Message` object as the argument (e.g. `display_name = get_name_string(ctx.message)`).
  This will return either a discord username, formatted correctly, or an irc nickname depending on the source of the message.
  Finally, this can be used as normal in a format string e.g. `await ctx.send(f'Sorry {display_name}, that won't work.')`.

- When writing a new command, please read in the rest of the message using `*args: clean_content` (see `cogs/commands/flip.py` as an example), and if you need it as one large string, use `" ".join(args)`.
  This is instead of reading the whole message content, which will likely break the irc bridging (unless you know what you're doing).

- This project uses the Black Python formatter.
  Before submitting your code for a PR, run `black .` on the root directory of this project to bring all of your up to spec for the code style guide.
- For testing CI locally, use [act-cli](https://github.com/nektos/act).

- The current production database engine is PostgreSQL.
  You may wish to use another database engine such as MySQL or SQLite for local testing.

- To create a DB migration:
  1. Create model in `/models`
  2. Import in `/models/__init__.py`
  3. Run `alembic revision --autogenerate -m "<change description>"`
  4. Check the newly created upgrade and downgrade is correct
  5. Upgrade your database with `alembic upgrade head`

### Testing subsections

You may want to work on a subsection of the bot without the surrounding functionality. This may be useful if you want to add a basic command but don't want the hassle of installing and working around the database requirements. You can disable parts of the bot from being loaded in at runtime by disabling their cogs.

[Cogs](https://discordpy.readthedocs.io/en/stable/ext/commands/cogs.html) are a method of categorising parts of your bot with discord.py. If you are to contribute to the project, some understanding of cogs and discord.py in general would be advisable, but you can see the implementation of pre-existing commands for a basic idea of how they work.

Cogs are loaded in [apollo.py](apollo.py):

```py
# The command extensions to be loaded by the bot
EXTENSIONS = [
    "cogs.commands.admin",
    "cogs.commands.blacklist",
    "cogs.commands.date",
    "cogs.commands.flip",
    "cogs.commands.karma",
    "cogs.commands.misc",
    # ...and so on
]
```

You can simply comment out any category of commands you don't want the bot to load to avoid supporting their requirements:

```py
# The command extensions to be loaded by the bot
EXTENSIONS = [
    "cogs.commands.admin",
    #    "cogs.commands.blacklist", # <- requires database
    "cogs.commands.date",
    "cogs.commands.flip",
    #    "cogs.commands.karma", # <- requires database
    "cogs.commands.misc",
    # ...and so on
]
```

Make sure not to commit these comments when you pull request.
