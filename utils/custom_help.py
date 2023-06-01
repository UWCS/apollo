import discord
from discord.ext import commands


# Modified from https://pypi.org/project/discord-simple-pretty-help/
class SimplePrettyHelp(commands.HelpCommand):
    def __init__(self, color=0x5865F2):
        super().__init__()
        self.color = color

    async def send_bot_help(self, mapping):
        """Main help menu"""

        await self.get_destination().send(
            embed=discord.Embed.from_dict(
                {
                    "color": self.color,
                    "fields": [
                        {
                            "name": getattr(cog, "qualified_name", "Others"),
                            "value": "\n".join(
                                (
                                    f"⠀- `{command.name}`"
                                    f"{('', f': {command.brief}')[bool(command.brief)]}"
                                )
                                for command in commands
                            )
                            or "⠀No commands",
                            "inline": False,
                        }
                        for cog, commands in mapping.items()
                    ],
                    "footer": {
                        "text": "For more information on a command : !help [command]"
                    },
                }
            )
        )

    async def send_command_help(self, command):
        """Command help menu"""
        print(repr(command))

        await self.get_destination().send(
            embed=discord.Embed.from_dict(
                {
                    "color": self.color,
                    "title": command.name,
                    "description": command.brief or "",
                    "fields": [
                        {
                            "name": "Usage",
                            "value": (
                                f"```\n{self.context.clean_prefix}{command.name}"
                                f"{' '.join(f'[{arg}]' for arg in command.clean_params)}\n```"
                            ),
                        },
                        {
                            "name": "Arguments",
                            "value": "\n".join(
                                (
                                    f"⠀- **{arg}**"
                                    f"""{("", f": {command.extras.get('args', {}).get(arg, '')}")[arg in command.extras.get("args", {})]}"""
                                )
                                for arg in command.clean_params
                            )
                            or "⠀No arguments",
                        },
                        {
                            "name": "Aliases",
                            "value": ", ".join(
                                [f"`{command.name}`"]
                                + [f"`{alias}`" for alias in command.aliases]
                            ),
                        },
                    ],
                }
            )
        )

    async def send_group_help(self, group):
        """Group help menu"""

        await self.get_destination().send(
            embed=discord.Embed.from_dict(
                {
                    "color": self.color,
                    "title": group.name,
                    "description": group.brief or "",
                    "fields": [
                        {
                            "name": "Usage",
                            "value": (
                                f"```\n{self.context.clean_prefix}{group.name}"
                                f"{' '.join(f'[{arg}]' for arg in group.clean_params)}\n```"
                            ),
                        },
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
                        },
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
                        },
                        {
                            "name": "Aliases",
                            "value": ", ".join(
                                [f"`{group.name}`"]
                                + [f"`{alias}`" for alias in group.aliases]
                            ),
                        },
                    ],
                    "footer": {
                        "text": "For more information on a command : !help [command]"
                    },
                }
            )
        )

    async def send_cog_help(self, cog):
        """Cog help menu"""

        await self.get_destination().send(
            embed=discord.Embed.from_dict(
                {
                    "color": self.color,
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
