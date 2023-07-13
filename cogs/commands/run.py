import logging
from enum import Enum

import aiohttp
from discord.ext import commands
from discord.ext.commands import Bot, Context

from config import CONFIG


# pyromaniac data model
class Language(Enum):
    Python = "Python"
    Rust = "Rust"
    Java = "Java"

    @staticmethod
    def from_str(lang: str):
        match lang.lower():
            case "py" | "python":
                return Language.Python
            case "java" | "jar":
                return Language.Java
            case "rust" | "rs":
                return Language.Rust
            case "":
                raise Exception(f"No language provided!")
            case _:
                raise Exception(f"Language '{lang}' not supported!")


LONG_HELP_TEXT = """Run some code using our Firecracker VM execution backend, Pyromaniac. 
Usage:
!run "<input>"
```
code
```

Supported languages:
- Python
- Rust
- Java
"""

SHORT_HELP_TEXT = """Run some code!"""


class Run(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(help=LONG_HELP_TEXT, brief=SHORT_HELP_TEXT)
    async def run(self, ctx: Context[Bot]):
        content = ctx.message.content
        code_block = content.split("```")[1]

        # yes, this is cringe parsing and even cringer error handling
        # this codebase is a mess anyway
        # cry about it
        try:
            language = Language.from_str(code_block.splitlines()[0])
        except Exception as e:
            await ctx.reply(
                "Could not parse language from code block. Did you specify the language?"
            )
            logging.error("Parse error: ", e)
            return

        try:
            code = "\n".join(code_block.splitlines()[1:])
        except Exception as e:
            await ctx.reply(
                "Could not parse code from message. Make sure you include a code block."
            )
            logging.error("Parse error: ", e)
            return

        try:
            input = content.split("```")[0].rstrip("\n").lstrip("!run ")
        except Exception as e:
            await ctx.reply(
                "Could not parse input from message. Include the input before the code block."
            )
            logging.error("Parse error: ", e)
            return

        json_request = {"code": code, "lang": str(language.value), "input": input}

        await ctx.message.add_reaction("⏳")

        async with aiohttp.ClientSession() as session:
            run_endpoint = CONFIG.PYROMANIAC_URL + "/api/run"
            response = await session.post(run_endpoint, json=json_request)
            if not response.ok:
                body = await response.text()
                logging.error(response)
                logging.error(body)
                await ctx.reply("Internal error")
                return

            json_response = await response.json()

        if err := json_response.get("error") is not None:
            await ctx.reply(f"Error from Pyromaniac backend: {err}")
        else:
            stdout: str = json_response.get("stdout")
            stderr: str = json_response.get("stderr")
            match (stdout, stderr):
                case ("", ""):
                    await ctx.reply("**Code executed succesfully, no output**")
                case (_, ""):
                    await ctx.reply(f"**Code Output**: \n ```\n{stdout}\n```")
                case ("", _):
                    await ctx.reply(f"**Code returned errors:**: \n ```\n{stderr}\n```")
                case (_, _):
                    await ctx.reply(
                        f"**Code returned both output and errors.**\n **Output:**\n{stdout}\n**Errors:**\n{stderr}"
                    )

        assert self.bot.user
        await ctx.message.remove_reaction("⏳", self.bot.user)


async def setup(bot: Bot):
    if CONFIG.PYROMANIAC_URL:
        await bot.add_cog(Run(bot))
    else:
        logging.warn("No Pyromaniac API give, not loading code runner")
