from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, TelegramObject

from vpn_core.telegram_bot.handlers.common import answer_callback


class CallbackGuardMiddleware(BaseMiddleware):
    """Ensure callback queries are always answered so Telegram buttons stop loading."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)

        answered = False

        async def mark_answered() -> None:
            nonlocal answered
            answered = True

        data["mark_callback_answered"] = mark_answered

        try:
            return await handler(event, data)
        except Exception:
            if not answered:
                await answer_callback(
                    event,
                    "⚠️ خطایی رخ داد. دوباره تلاش کن.",
                    show_alert=True,
                )
                answered = True
            raise
        finally:
            if not answered:
                await answer_callback(event)
