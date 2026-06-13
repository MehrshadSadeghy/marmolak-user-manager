from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.config import TelegramBotConfig
from vpn_core.telegram_bot.handlers.common import ensure_user, telegram_id, edit_callback_message
from vpn_core.telegram_bot.keyboards.main import main_menu_keyboard
from vpn_core.telegram_bot.messages import main_menu_message, welcome_message

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, api: UserManagerApiClient, bot_config: TelegramBotConfig) -> None:
    user = await ensure_user(api, message)
    is_admin = telegram_id(message) in bot_config.admin_chat_ids
    await message.answer(
        welcome_message(user["user"]["id"], user["wallet_balance_toman"]),
        reply_markup=main_menu_keyboard(is_admin),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "menu:home")
async def menu_home(
    callback: CallbackQuery,
    state: FSMContext,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    await state.clear()
    message = callback.message
    if not message:
        await callback.answer()
        return
    user = await ensure_user(api, message)
    is_admin = str(callback.from_user.id) in bot_config.admin_chat_ids
    await edit_callback_message(message, 
        main_menu_message(user["wallet_balance_toman"]),
        reply_markup=main_menu_keyboard(is_admin),
        parse_mode="HTML",
    )
    await callback.answer()
