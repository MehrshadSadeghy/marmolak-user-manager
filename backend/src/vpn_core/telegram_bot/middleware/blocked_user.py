from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.config import TelegramBotConfig
from vpn_core.telegram_bot.handlers.common import is_admin

BLOCKED_USER_MESSAGE = (
    "🚫 <b>حساب کاربری شما مسدود شده است</b>\n\n"
    "دسترسی شما توسط مدیر سیستم محدود شده است.\n"
    "برای پیگیری با پشتیبانی تماس بگیرید."
)

ALLOWED_CALLBACKS = {"menu:support"}


class BlockedUserMiddleware(BaseMiddleware):
    def __init__(self, bot_config: TelegramBotConfig):
        self._bot_config = bot_config

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = self._extract_user_id(event)
        if user_id is None:
            return await handler(event, data)

        if is_admin(user_id, self._bot_config):
            return await handler(event, data)

        if self._is_allowed_event(event):
            return await handler(event, data)

        api: UserManagerApiClient = data["api"]
        try:
            access = await api.get_user_access(str(user_id))
        except Exception:
            return await handler(event, data)

        if not access.get("is_blocked"):
            return await handler(event, data)

        if isinstance(event, CallbackQuery):
            message = event.message
            if message:
                await message.answer(BLOCKED_USER_MESSAGE, parse_mode="HTML")
            await event.answer("حساب شما مسدود است", show_alert=True)
            return None

        if isinstance(event, Message):
            await event.answer(BLOCKED_USER_MESSAGE, parse_mode="HTML")
            return None

        return await handler(event, data)

    @staticmethod
    def _extract_user_id(event: TelegramObject) -> int | None:
        if isinstance(event, Message) and event.from_user:
            return event.from_user.id
        if isinstance(event, CallbackQuery) and event.from_user:
            return event.from_user.id
        return None

    @staticmethod
    def _is_allowed_event(event: TelegramObject) -> bool:
        if isinstance(event, Message):
            text = (event.text or "").strip()
            return text.startswith("/start")
        if isinstance(event, CallbackQuery):
            return event.data in ALLOWED_CALLBACKS
        return False
