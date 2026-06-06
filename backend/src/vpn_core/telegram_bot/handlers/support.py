from aiogram import F, Router
from aiogram.types import CallbackQuery

from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.keyboards.main import back_to_menu_keyboard

router = Router()


@router.callback_query(F.data == "menu:support")
async def menu_support(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    support = await api.get_support()
    username = support.get("support_username")
    if username:
        text = f"Contact support: @{username.lstrip('@')}"
    else:
        text = "Support username is not configured yet. Please contact the administrator."
    await message.edit_text(text, reply_markup=back_to_menu_keyboard())
    await callback.answer()
