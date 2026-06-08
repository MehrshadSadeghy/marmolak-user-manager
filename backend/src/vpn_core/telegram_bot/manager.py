import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from vpn_core.core.manager.base import Manager
from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.config import TelegramBotConfig
from vpn_core.telegram_bot.handlers import register_handlers
from vpn_core.telegram_bot.middleware.blocked_user import BlockedUserMiddleware
from vpn_core.telegram_bot.middleware.context import BotContextMiddleware

LOGGER = logging.getLogger(__name__)


class TelegramBotManager(Manager):
    def __init__(self, bot_config: TelegramBotConfig):
        self._config = bot_config
        self._bot: Bot | None = None
        self._dispatcher: Dispatcher | None = None

    async def setup(self) -> None:
        LOGGER.info("Setting up Telegram bot")
        self._bot = Bot(token=self._config.token)
        self._dispatcher = Dispatcher(storage=MemoryStorage())
        api = UserManagerApiClient(self._config.api_base_url, self._config.bot_api_key)
        self._dispatcher.update.middleware(BotContextMiddleware(api, self._config))
        self._dispatcher.update.middleware(BlockedUserMiddleware(self._config))
        register_handlers(self._dispatcher)

    async def run(self) -> None:
        if not self._bot or not self._dispatcher:
            raise ValueError("TelegramBotManager is not setup")
        LOGGER.info("Running Telegram bot")
        await self._dispatcher.start_polling(self._bot)

    async def teardown(self) -> None:
        if self._bot:
            await self._bot.session.close()
