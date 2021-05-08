from pathlib import Path

import yaml


class Config:
    def __init__(self, filepath):
        with open(filepath) as f:
            parsed = yaml.full_load(f).get("config")

        self.UWCS_DISCORD_BRIDGE_BOT_ID: int = parsed.get("UWCS_discord_bridge_bot_id")
        self.UWCS_MEMBER_ROLE_ID: int = parsed.get("UWCS_member_role_id")
        self.UWCS_EXEC_ROLE_IDS: list[int] = parsed.get("UWCS_exec_role_ids")
        self.UWCS_WELCOME_CHANNEL_ID: int = parsed.get("UWCS_welcome_channel_id")
        self.UWCS_INTROS_CHANNEL_ID: int = parsed.get("UWCS_intros_channel_id")
        self.UWCS_AUTOMOD_LOG_CHANNEL_ID: int = parsed.get("UWCS_automod_log_channel_id")
        self.UWCS_JOIN_LEAVE_LOG_CHANNEL_ID: int = parsed.get("UWCS_join_leave_log_channel_id")
        self.UWCS_MEMBER_LOG_CHANNEL_ID: int = parsed.get("UWCS_member_log_channel_id")
        self.UWCS_MESSAGE_LOG_CHANNEL_ID: int = parsed.get("UWCS_message_log_channel_id")
        self.UWCS_VOICE_LOG_CHANNEL_ID: int = parsed.get("UWCS_voice_log_channel_id")
        self.DATABASE_CONNECTION: str = parsed.get("database_connection")
        self.UWCS_DISCORD_ID: int = parsed.get("UWCS_discord_id")
        self.UWCS_API_TOKEN: str = parsed.get("UWCS_api_token")
        self.BOT_SECRET_KEY: str = parsed.get("bot_secret_key")
        self.KARMA_TIMEOUT: int = parsed.get("karma_timeout")
        self.DISCORD_TOKEN: str = parsed.get("discord_token")
        self.FIG_SAVE_PATH: Path = Path(parsed.get("fig_save_path"))
        self.FIG_HOST_URL: str = parsed.get("fig_host_url")
        self.SQL_LOGGING: bool = parsed.get("sql_logging")
        self.BOT_LOGGING: bool = parsed.get("bot_logging")
        self.DEBUG: bool = parsed.get("debug")
        self.REMINDER_SEARCH_INTERVAL: int = parsed.get("reminder_search_interval")
        self.SLICER_PATH: Path = Path(parsed.get("slicer_path"))
        self.PRINTER_FILE_ROOT: Path = Path(parsed.get("printer_file_root"))


CONFIG = Config("config.yaml")
