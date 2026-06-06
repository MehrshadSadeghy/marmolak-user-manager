from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.config import TelegramBotConfig


class BotContextMiddleware(BaseMiddleware):
    def __init__(self, api: UserManagerApiClient, bot_config: TelegramBotConfig):
        self._api = api
        self._bot_config = bot_config

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        data["api"] = self._api
        data["bot_config"] = self._bot_config
        return await handler(event, data)
