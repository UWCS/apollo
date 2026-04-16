from typing import Any, Mapping

from discord import Embed
from discord.ext.commands import Cog, Command, Group, HelpCommand


# Modified from https://pypi.org/project/discord-simple-pretty-help/
class SimplePrettyHelp(HelpCommand):
    def __init__(self, colour: int = 0x5865F2) -> None:
        super().__init__()
        self.colour = colour

    async def send_bot_help(self, mapping: Mapping[Cog | None, list[Command[Any, ..., Any]]]) -> None:
        """Main help menu"""

        cog_fields: list[dict[str, str | bool]] = []
        for cog, cmds in mapping.items():
            name: str = getattr(cog, "qualified_name", "Others")
            if name == "Misc" or not cmds:
                continue
            cog_fields.append(
                {
                    "name": name,
                    "value": "\n".join(
                        (f"⠀- `{command.name}` {command.brief or ''}")
                        for command in cmds
                    ),
                    "inline": False,
                }
            )

        await self.get_destination().send(
            embed=Embed.from_dict(
                {
                    "colour": self.colour,
                    "fields": cog_fields,
                    "footer": {
                        "text": "For more information on a command : !help [command]"
                    },
                }
            )
        )

    async def send_command_help(self, command: Command[Any, ..., Any]) -> None:
        """Command help menu"""
        #print(repr(command))
        fields = [
            {
                "name": "Usage",
                "value": (
                    f"```\n{self.context.clean_prefix}{command.name} {command.signature}\n```"
                ),
            },
        ]

        if command.clean_params:
            fields.append(
                {
                    "name": "Arguments",
                    "value": "\n".join(
                        (
                            f"⠀- **{arg}**"
                            f"""{("", f": {command.extras.get('args', {}).get(arg, '')}")[arg in command.extras.get("args", {})]}"""
                        )
                        for arg in command.clean_params
                    ),
                }
            )
        if command.aliases:
            fields.append(
                {
                    "name": "Aliases",
                    "value": ", ".join(
                        [f"`{command.name}`"]
                        + [f"`{alias}`" for alias in command.aliases]
                    ),
                }
            )

        await self.get_destination().send(
            embed=Embed.from_dict(
                {
                    "colour": self.colour,
                    "title": command.name,
                    "description": command.help or command.brief or "",
                    "fields": fields,
                }
            )
        )

    async def send_group_help(self, group: Group[Any, ..., Any]) -> None:
        """Group help menu"""
        fields = [
            {
                "name": "Usage",
                "value": (
                    f"```\n{self.context.clean_prefix}{group.name} {group.signature}\n```"
                ),
            }
        ]

        if group.clean_params:
            fields.append(
                {
                    "name": "Arguments",
                    "value": "\n".join(
                        (
                            f"⠀- **{arg}**"
                            f"""{("", f": {group.extras.get('args', {}).get(arg, '')}")[arg in group.extras.get("args", {})]}"""
                        )
                        for arg in group.clean_params
                    )
                    or "⠀No arguments",
                }
            )

        if group.commands:
            fields.append(
                {
                    "name": "Subcommands",
                    "value": "\n".join(
                        (
                            f"⠀- **{subcommand.name}**"
                            f"""{("", f": {subcommand.brief}")[bool(subcommand.brief)]}"""
                        )
                        for subcommand in group.commands
                    )
                    or "⠀No subcommands",
                }
            )

        if group.aliases:
            fields.append(
                {
                    "name": "Aliases",
                    "value": ", ".join([f"`{alias}`" for alias in group.aliases]),
                }
            )

        await self.get_destination().send(
            embed=Embed.from_dict(
                {
                    "colour": self.colour,
                    "title": group.name,
                    "description": group.brief or "",
                    "fields": fields,
                    "footer": {
                        "text": "For more information on a command : !help [command]"
                    },
                }
            )
        )

    async def send_cog_help(self, cog: Cog) -> None:
        """Cog help menu"""

        await self.get_destination().send(
            embed=Embed.from_dict(
                {
                    "colour": self.colour,
                    "title": cog.qualified_name,
                    "description": cog.description,
                    "fields": [
                        {
                            "name": "Commands",
                            "value": "\n".join(
                                (
                                    f"⠀- `{command.name}`"
                                    f"{('', f': {command.brief}')[bool(command.brief)]}"
                                )
                                for command in cog.get_commands()
                            ),
                        }
                    ],
                    "footer": {
                        "text": "For more information on a command : !help [command]"
                    },
                }
            )
        )
