import os
from dataclasses import dataclass

from vpn_core.common.auth.bot_api_key import get_admin_chat_ids, parse_chat_ids


@dataclass(frozen=True)
class TelegramBotConfig:
    token: str
    api_base_url: str
    bot_api_key: str
    admin_chat_ids: set[str]

    @classmethod
    def from_env(cls) -> "TelegramBotConfig | None":
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            return None
        return cls(
            token=token,
            api_base_url=os.getenv("USER_MANAGER_API_URL", "http://127.0.0.1:8080").rstrip("/"),
            bot_api_key=os.getenv("BOT_API_KEY", "changeme-bot-api-key"),
            admin_chat_ids=get_admin_chat_ids(),
        )
