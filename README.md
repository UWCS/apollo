# Apollo [![Build Status](https://travis-ci.org/UWCS/apollo.svg?branch=master)](https://travis-ci.org/uwcs/apollo)

Apollo is a [Discord](https://discordapp.com/) bot for the [University of Warwick Computing Society](https://uwcs.co.uk). It is designed to augment our Discord server with a few of the user services available on our website.

Apollo is based loosely on the development of [artemis](https://github.com/rhiannonmichelmore/artemis), another Discord bot produced by a member of UWCS.

### Installation

To run this bot, create a new Python virtual environment (version 3.6 or above) and use `pip install -r requirements.txt` to install all of the library requirements. You will also need to migrate the database using `alembic` after the Python libraries are installed.

### Contributor Notes

* When writing anything that needs to reply back to a specific username, please do `from utils import get_name_string` and get the display string using this function, with the discord `Message` object as the argument (e.g. `display_name = get_name_string(ctx.message)`). This will return either a discord username, formatted correctly, or an irc nickname depending on the source of the message. Finally, this can be used as normal in a format string e.g. `await ctx.send(f'Sorry {display_name}, that won't work.')`.

* When writing a new command, please read in the rest of the message using `*args: clean_content` (see `commands/flip.py` as an example), and if you need it as one large string, use `" ".join(args)`. This is instead of reading the whole message content, which will likely break the irc bridging (unless you know what you're doing).

* This project uses the Black Python formatter. Before submitting your code for a PR, run `black .` on the root directory of this project to bring all of your up to spec for the code style guide.

### License

This project is distributed under the MIT license.

The MIT License (MIT)
=====================

Copyright © 2018 David Richardson

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the “Software”), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
