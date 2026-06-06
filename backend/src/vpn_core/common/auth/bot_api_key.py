import os

from fastapi import Header, HTTPException


def get_bot_api_key() -> str:
    return os.getenv("BOT_API_KEY", "changeme-bot-api-key")


def parse_chat_ids(raw: str | None) -> set[str]:
    if not raw:
        return set()
    return {item.strip() for item in raw.split(",") if item.strip()}


def get_admin_chat_ids() -> set[str]:
    return parse_chat_ids(os.getenv("ADMIN_CHAT_IDS")) | parse_chat_ids(
        os.getenv("SUPER_ADMIN_CHAT_IDS")
    )


async def verify_bot_api_key(x_bot_api_key: str | None = Header(default=None)) -> None:
    expected = get_bot_api_key()
    if not x_bot_api_key or x_bot_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid bot API key")


async def verify_admin_telegram_id(
    x_admin_telegram_id: str | None = Header(default=None),
) -> str:
    if not x_admin_telegram_id or x_admin_telegram_id not in get_admin_chat_ids():
        raise HTTPException(status_code=403, detail="Admin access required")
    return x_admin_telegram_id
