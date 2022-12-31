# Apollo [![Build status](https://github.com/UWCS/apollo/actions/workflows/tests.yaml/badge.svg?branch=master)](https://github.com/UWCS/apollo/actions/workflows/tests.yaml)

Apollo is a [Discord](https://discordapp.com/) bot for the [University of Warwick Computing Society](https://uwcs.co.uk).
It is designed to augment our Discord server with a few of the user services available on our website.

### Installation

1. Create a new virtual environment `python -m venv venv`.
2. Activate the virtual environment
   - On Linux and macOS: `source venv/bin/activate`.
   - On Windows: `.\venv\Scripts\activate`
4. Install dependencies `pip install -r requirements.txt`
5. Copy `config.example.yaml` to `config.yaml` and configure the fields.
6. Copy `alembic.example.ini` to `alembic.ini`.
7. Set up the database by running migrations with `alembic upgrade head`.
   - In production, Postgres is recommended instead of SQLite.
8. On the [Discord Developer Portal](https://discord.com/developers/), create your bot and give it member and message content intents.
9. Run `python apollo.py`.