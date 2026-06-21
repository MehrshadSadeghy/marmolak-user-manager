import httpx
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.config import TelegramBotConfig
from vpn_core.telegram_bot.handlers.common import handle_admin_api_error, edit_callback_message
from vpn_core.telegram_bot.handlers.menu_helpers import pasarguard_menu_enabled
from vpn_core.telegram_bot.keyboards.main import back_to_menu_keyboard, main_menu_keyboard
from vpn_core.telegram_bot.messages import status_label_fa
from vpn_core.telegram_bot.states import UserFlow

router = Router()


@router.callback_query(F.data == "menu:config-traffic")
async def menu_config_traffic(
    callback: CallbackQuery,
    state: FSMContext,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    await state.set_state(UserFlow.waiting_config_id)
    await edit_callback_message(message, 
        "📊 <b>استعلام حجم کانفیگ</b>\n\n"
        "🔢 کد ۱۰ رقمی کانفیگ را بفرست.\n"
        "💡 این کد همان نام فایل <code>XXXXXXXXXX.ovpn</code> است.\n\n"
        "برای لغو، «بازگشت به منو» را بزن.",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(UserFlow.waiting_config_id, F.text)
async def receive_config_id(
    message: Message,
    state: FSMContext,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    config_id = (message.text or "").strip()
    if not config_id.isdigit() or len(config_id) != 10:
        await message.answer(
            "⚠️ کد کانفیگ باید دقیقاً <b>۱۰ رقم</b> باشد.\n"
            "مثال: <code>0123456789</code>",
            parse_mode="HTML",
        )
        return

    tg_id = str(message.from_user.id)
    try:
        result = await api.get_openvpn_config_traffic(tg_id, config_id)
    except httpx.HTTPStatusError as exc:
        if await handle_admin_api_error(message, exc):
            return
        if exc.response.status_code == 404:
            await message.answer(
                "❌ کانفیگ با این کد پیدا نشد.\n"
                "مطمئن شو کد را درست وارد کرده‌ای و این کانفیگ متعلق به حساب توست.",
                reply_markup=back_to_menu_keyboard(),
            )
            return
        raise

    await state.clear()
    status = status_label_fa(result["status_label"])
    is_admin = tg_id in bot_config.admin_chat_ids
    pasarguard_enabled = await pasarguard_menu_enabled(api)
    await message.answer(
        "📊 <b>وضعیت کانفیگ</b>\n\n"
        f"🆔 کد کانفیگ: <code>{result['config_id']}</code>\n"
        f"📦 اشتراک: <b>#{result['subscription_id']}</b>\n"
        f"📌 وضعیت: {status}\n"
        f"⏳ زمان باقی‌مانده: <b>{result['remaining_days']} روز</b>\n"
        f"📈 حجم مصرف‌شده: <b>{result['used_data_label']}</b>\n"
        f"📦 سقف حجم: <b>{result['limit_data_label']}</b>\n"
        f"📉 حجم باقی‌مانده: <b>{result['remaining_data_label']}</b>\n"
        f"📅 انقضا: {result['expire_at'][:10]}",
        reply_markup=main_menu_keyboard(is_admin, pasarguard_enabled=pasarguard_enabled),
        parse_mode="HTML",
    )
