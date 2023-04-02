# Apollo [![Build status](https://github.com/UWCS/apollo/actions/workflows/ci.yaml/badge.svg?branch=master)](https://github.com/UWCS/apollo/actions/workflows/ci.yaml)

Apollo is a [Discord](https://discordapp.com/) bot for the [University of Warwick Computing Society](https://uwcs.co.uk).
It is designed to augment our Discord server with a few of the user services available on our website.

### Installation

#### Dependencies

Apollo uses `pipenv` for dependency and venv management. Install it with `pip install pipenv`, and then run `pipenv install` to install all the required dependencies into a new virtual environment.

#### Development Setup

1. `pipenv install`, as above
2. Copy `config.example.yaml` to `config.yaml` and configure the fields.
3. Copy `alembic.example.ini` to `alembic.ini` and configure any fields you wish to change.
4. Set up the database by running migrations with `alembic upgrade head`.
   - The default database location is `postgresql://apollo:apollo@localhost/apollo` (in `config.example.yaml`)
     This requires PostgreSQL to be installed, with a database called `apollo` and a user with name and password `apollo` with access to it.
   - For testing purposes, you may wish to change it to a locally stored file such as `sqlite:///apollo.sqlite3`. 
   - Alternatively, see the instructions below for using Docker.
5. On the [Discord Developer Portal](https://discord.com/developers/), make sure that your bot has the required intents.
   - Currently, the Messages and Members intents are necessary.

Run Apollo using `pipenv run python apollo.py`

#### Using Docker

A Dockerfile and docker-compose are provided for easily running Apollo. Assuming you already have docker installed, run `docker compose up` to start both Apollo and a postgres database.

The compose file uses a read-only bind mount to mount `config.yaml` into the container at runtime, not at build time. Copy `config.example.yaml` to `config.yaml` and configure the fields so that compose can do this. You will need to change the database url to `postgresql://apollo:apollo@apollo-db/apollo` if you wish to connect to the containerised database.

The docker image builds `alembic.ini` into it by copying the example, as it is rare any values in this wish to be changed on a per-deployment basis.

When you first create the database container, you'll need to apply migrations:

1. Run `docker compose up` to start both services. The python one won't work, but leave it running.
   - When changing any source files, the container will have to be rebuilt: `docker compose up --build`
2. Run `docker compose exec apollo alembic upgrade head` to apply the database migrations.
3. Run `docker compose restart apollo` to restart the bot with migrations applied.

Migrations will need to be re-applied every time the database schema changes.

### Contributing
Check [our issues](https://github.com/UWCS/apollo/contribute) for ideas of what to [contribute](https://github.com/UWCS/apollo/contribute). If you want to see a particular feature that isn't mentioned, feel free to work on it (but please do make an issue beforehand, so we can discuss it)

See our wiki for a general overview of the project and and [Contributor Notes](https://github.com/UWCS/apollo/wiki/Contributing-Notes) for project specific advice and utility.
