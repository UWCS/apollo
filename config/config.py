from pathlib import Path

import yaml


class Config:
    def __init__(self, filepath):
        with open(filepath) as f:
            parsed = yaml.full_load(f).get("config")

        # Essential
        self.PREFIX: str = parsed.get("prefix")
        self.UWCS_DISCORD_ID: int = parsed.get("UWCS_discord_id")
        self.UWCS_EXEC_ROLE_IDS: list[int] = parsed.get("UWCS_exec_role_ids")
        self.DISCORD_TOKEN: str = parsed.get("discord_token")
        self.BOT_SECRET_KEY: str = parsed.get("db_secret_key")
        self.DATABASE_CONNECTION: str = parsed.get("database_connection")

        # Optional
        self.UWCS_WELCOME_CHANNEL_ID: int = parsed.get("UWCS_welcome_channel_id")
        self.UWCS_ROLES_CHANNEL_ID: int = parsed.get("UWCS_roles_channel_id")
        self.UWCS_EXEC_SPAM_CHANNEL_ID: int = parsed.get("UWCS_exec_spam_channel_id")
        self.UWCS_DISCORD_BRIDGE_BOT_ID: int = parsed.get("UWCS_discord_bridge_bot_id")
        self.OPENAI_API_KEY: str = parsed.get("openai_api_key")
        self.AI_INCLUDE_NAMES: bool = parsed.get("ai_include_names")
        self.AI_CHAT_CHANNELS: list[int] = parsed.get("ai_chat_channels")
        self.AI_SYSTEM_PROMPT: str = parsed.get("ai_system_prompt")
        self.PORTAINER_API_KEY: str = parsed.get("portainer_api_key")

        # Configuration
        self.LOG_LEVEL: str = parsed.get("log_level")
        self.SQL_LOGGING: bool = parsed.get("log_sql")
        self.KARMA_TIMEOUT: int = parsed.get("karma_cooldown")
        self.REMINDER_SEARCH_INTERVAL: int = parsed.get("reminder_search_interval")
        self.CHANNEL_CHECK_INTERVAL: int = parsed.get("channel_check_interval")
        self.ANNOUNCEMENT_SEARCH_INTERVAL: int = parsed.get(
            "announcement_search_interval"
        )
        self.ANNOUNCEMENT_IMPERSONATE: int = parsed.get("announcement_impersonate")
        self.UNICODE_NORMALISATION_FORM: str = "NFKD"

        # Unused
        self.UWCS_MEMBER_ROLE_ID: int = parsed.get("UWCS_member_role_id")
        self.UWCS_API_TOKEN: str = parsed.get("UWCS_api_token")
        self.SLICER_PATH: Path = Path(parsed.get("slicer_path"))
        self.PRINTER_FILE_ROOT: Path = Path(parsed.get("printer_file_root"))


CONFIG = Config("config.yaml")
