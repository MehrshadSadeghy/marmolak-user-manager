from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.config import TelegramBotConfig
from vpn_core.telegram_bot.handlers.common import ensure_user, telegram_id
from vpn_core.telegram_bot.keyboards.main import main_menu_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, api: UserManagerApiClient, bot_config: TelegramBotConfig) -> None:
    user = await ensure_user(api, message)
    is_admin = telegram_id(message) in bot_config.admin_chat_ids
    await message.answer(
        "Welcome to VPN User Manager.\n"
        f"Your ID: {user['user']['id']}\n"
        f"Wallet balance: {user['wallet_balance_toman']} Toman\n\n"
        "Choose an option:",
        reply_markup=main_menu_keyboard(is_admin),
    )


@router.callback_query(F.data == "menu:home")
async def menu_home(callback: CallbackQuery, api: UserManagerApiClient, bot_config: TelegramBotConfig) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    user = await ensure_user(api, message)
    is_admin = str(callback.from_user.id) in bot_config.admin_chat_ids
    await message.edit_text(
        "Main menu\n"
        f"Wallet balance: {user['wallet_balance_toman']} Toman",
        reply_markup=main_menu_keyboard(is_admin),
    )
    await callback.answer()
