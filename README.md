# Apollo [![Build status](https://github.com/UWCS/apollo/actions/workflows/tests.yaml/badge.svg?branch=master)](https://github.com/UWCS/apollo/actions/workflows/tests.yaml)

Apollo is a [Discord](https://discordapp.com/) bot for the [University of Warwick Computing Society](https://uwcs.co.uk).
It is designed to augment our Discord server with a few of the user services available on our website.

### Installation

#### Dependencies

Apollo uses `pipenv` for dependency and venv management. Install it with `pip install pipenv`, and then run `pipenv install` to install all the required dependencies into a new virtual environment.

#### Development Setup

1. `pipenv install`, as above
2. Copy `config.example.yaml` to `config.yaml` and configure the fields.
3. Copy `alembic.example.ini` to `alembic.ini`.
4. Set up the database by running migrations with `alembic upgrade head`.
   - The default database location is `postgresql://apollo:apollo@localhost/apollo` (in both `config.example.yaml` and `alembic.example.ini`).
     This requires PostgreSQL to be installed, with a database called `apollo` and a user with name and password `apollo` with access to it.
     For testing purposes, you may wish to change it to a locally stored file such as `sqlite:///local.sqlite3`. Alternatively, see the instructions below for using Docker.
5. On the [Discord developer portal](https://discord.com/developers/), make sure that your bot has the required intents.
   - Currently, only the Members intent is necessary.

Run Apollo using `pipenv run python apollo.py`

#### Using Docker

A Dockerfile and docker-compose are provided for easily running Apollo. Assuming you already have docker installed, run `docker compose up` to start both Apollo and a postgres database. If `config.yaml` or `alembic.ini` are not present, the dockerfile will use the example config files, with some changes applied to connect to the containerised database. If you wish to provide your own `config.yaml` and use the containerised database, the URL is `postgresql://apollo:apollo@apollo-db/apollo`

When you first create the database container, you'll need to apply migrations:

1. Run `docker compose up` to start both services. The python one won't work, but leave it running.
   - When changing any source files, the container will have to be rebuilt: `docker compose up --build`
2. Run `docker compose exec apollo alembic upgrade head` to apply the database migrations.
3. Run `docker compose restart apollo` to restart the bot with migrations applied.

Migrations will need to be re-applied every time the database schema changes.

### Contributor Notes

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

#### Testing subsections

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
