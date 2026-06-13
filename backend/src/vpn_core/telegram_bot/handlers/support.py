from aiogram import F, Router
from aiogram.types import CallbackQuery
from vpn_core.telegram_bot.handlers.common import edit_callback_message

from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.keyboards.main import buy_now_keyboard

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
        text = (
            "💬 <b>پشتیبانی</b>\n\n"
            f"👤 برای ارتباط با پشتیبانی:\n"
            f"@{username.lstrip('@')}\n\n"
            "🛒 سوالی درباره خرید داری؟ همین الان پیام بده!\n"
            "⚡ تیم ما سریع پاسخ می‌دهد."
        )
    else:
        text = (
            "💬 <b>پشتیبانی</b>\n\n"
            "😔 نام کاربری پشتیبانی هنوز تنظیم نشده.\n"
            "📞 لطفاً با مدیر سیستم تماس بگیرید."
        )
    await edit_callback_message(message, 
        text,
        reply_markup=buy_now_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer("💬 پشتیبانی")
