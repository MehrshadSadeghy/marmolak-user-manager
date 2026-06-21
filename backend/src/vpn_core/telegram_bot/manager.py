import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramNetworkError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ErrorEvent

from vpn_core.core.manager.base import Manager
from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.config import TelegramBotConfig
from vpn_core.telegram_bot.handlers import register_handlers
from vpn_core.telegram_bot.handlers.common import answer_callback
from vpn_core.telegram_bot.middleware.blocked_user import BlockedUserMiddleware
from vpn_core.telegram_bot.middleware.callback_guard import CallbackGuardMiddleware
from vpn_core.telegram_bot.middleware.context import BotContextMiddleware

LOGGER = logging.getLogger(__name__)

POLLING_RETRY_SECONDS = 5
TELEGRAM_SESSION_TIMEOUT_SECONDS = 90.0


class TelegramBotManager(Manager):
    def __init__(self, bot_config: TelegramBotConfig):
        self._config = bot_config
        self._bot: Bot | None = None
        self._dispatcher: Dispatcher | None = None
        self._session: AiohttpSession | None = None

    async def setup(self) -> None:
        LOGGER.info("Setting up Telegram bot")
        self._session = AiohttpSession(timeout=TELEGRAM_SESSION_TIMEOUT_SECONDS)
        self._bot = Bot(token=self._config.token, session=self._session)
        self._dispatcher = Dispatcher(storage=MemoryStorage())
        api = UserManagerApiClient(self._config.api_base_url, self._config.bot_api_key)
        self._dispatcher.update.middleware(BotContextMiddleware(api, self._config))
        self._dispatcher.update.middleware(BlockedUserMiddleware(self._config))
        self._dispatcher.update.middleware(CallbackGuardMiddleware())
        register_handlers(self._dispatcher)

        @self._dispatcher.errors()
        async def on_handler_error(event: ErrorEvent) -> bool:
            LOGGER.exception("Telegram bot handler failed", exc_info=event.exception)
            if event.update.callback_query:
                await answer_callback(
                    event.update.callback_query,
                    "⚠️ خطایی رخ داد. دوباره تلاش کن.",
                    show_alert=True,
                )
            return True

    async def run(self) -> None:
        if not self._bot or not self._dispatcher:
            raise ValueError("TelegramBotManager is not setup")
        LOGGER.info("Running Telegram bot")
        while True:
            try:
                await self._dispatcher.start_polling(
                    self._bot,
                    handle_as_tasks=True,
                    polling_timeout=30,
                )
                break
            except TelegramNetworkError as exc:
                LOGGER.warning(
                    "Telegram polling network error, retrying in %ss: %s",
                    POLLING_RETRY_SECONDS,
                    exc,
                )
                await asyncio.sleep(POLLING_RETRY_SECONDS)
            except asyncio.CancelledError:
                raise
            except Exception:
                LOGGER.exception(
                    "Telegram polling crashed, retrying in %ss",
                    POLLING_RETRY_SECONDS,
                )
                await asyncio.sleep(POLLING_RETRY_SECONDS)

    async def teardown(self) -> None:
        if self._bot:
            await self._bot.session.close()
        self._bot = None
        self._session = None
