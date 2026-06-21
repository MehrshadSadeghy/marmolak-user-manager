import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.config import TelegramBotConfig
from vpn_core.telegram_bot.handlers.common import (
    edit_callback_message,
    guard_admin_callback,
    handle_admin_api_error,
    notify_user_chat,
)
from vpn_core.telegram_bot.handlers.menu_helpers import pasarguard_webapp_url
from vpn_core.telegram_bot.messages import PURPOSE_FA, format_toman, wallet_recharged_message
from vpn_core.telegram_bot.keyboards.main import admin_menu_keyboard, admin_plans_keyboard, admin_services_keyboard, buy_now_keyboard

router = Router()
LOGGER = logging.getLogger(__name__)


@router.callback_query(F.data == "menu:admin")
async def menu_admin(
    callback: CallbackQuery,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    webapp_url = await pasarguard_webapp_url(api)
    await edit_callback_message(message, 
        "⚙️ <b>پنل مدیریت</b>\n\n👇 یک گزینه را انتخاب کن:",
        reply_markup=admin_menu_keyboard(pasarguard_webapp_url=webapp_url),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin:payments")
async def admin_payments(callback: CallbackQuery, api: UserManagerApiClient, bot_config: TelegramBotConfig) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    payments = await api.list_pending_payments(str(callback.from_user.id))
    if not payments:
        await edit_callback_message(message, 
            "✅ پرداخت در انتظاری وجود ندارد.",
            reply_markup=admin_menu_keyboard(),
        )
    else:
        lines = []
        for p in payments:
            purpose = PURPOSE_FA.get(p["purpose"], p["purpose"])
            lines.append(
                f"🧾 #{p['id']} | کاربر {p['user_id']} | {format_toman(p['amount_toman'])} | {purpose}"
            )
        await edit_callback_message(message, 
            "⏳ <b>پرداخت‌های در انتظار</b>\n\n" + "\n".join(lines),
            reply_markup=admin_menu_keyboard(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "admin:services")
async def admin_services(callback: CallbackQuery, api: UserManagerApiClient, bot_config: TelegramBotConfig) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    services = await api.list_service_types_admin(str(callback.from_user.id))
    await edit_callback_message(message, 
        "🔧 <b>مدیریت انواع سرویس</b>\n\nروشن/خاموش کن:",
        reply_markup=admin_services_keyboard(services),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:toggle:"))
async def admin_toggle_service(callback: CallbackQuery, api: UserManagerApiClient, bot_config: TelegramBotConfig) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    _, _, action, slug = callback.data.split(":", 3)
    await api.toggle_service_type(str(callback.from_user.id), slug, action == "enable")
    services = await api.list_service_types_admin(str(callback.from_user.id))
    await edit_callback_message(message, 
        "🔧 <b>مدیریت انواع سرویس</b>\n\nروشن/خاموش کن:",
        reply_markup=admin_services_keyboard(services),
        parse_mode="HTML",
    )
    await callback.answer("✅ به‌روز شد")


@router.callback_query(F.data == "admin:plans")
async def admin_plans(callback: CallbackQuery, api: UserManagerApiClient, bot_config: TelegramBotConfig) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    try:
        plans = await api.list_plans_admin(str(callback.from_user.id))
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        raise
    if not plans:
        await edit_callback_message(message, 
            "📋 پلنی تعریف نشده.\n➕ می‌توانی پلن جدید اضافه کنی:",
            reply_markup=admin_plans_keyboard(),
        )
    else:
        lines = []
        for plan in plans:
            gb = plan["traffic_limit_bytes"] / (1024**3)
            lines.append(
                f"#{plan['id']} [{plan['service_type']}] {plan['name']} — "
                f"{gb:.0f}GB / {plan['duration_days']}روز — {format_toman(plan['price_toman'])}"
            )
        await edit_callback_message(message, 
            "📋 <b>لیست پلن‌ها</b>\n\n" + "\n".join(lines),
            reply_markup=admin_plans_keyboard(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:approve:"))
async def admin_approve(callback: CallbackQuery, api: UserManagerApiClient, bot_config: TelegramBotConfig) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    payment_id = int(callback.data.rsplit(":", 1)[1])
    try:
        result = await api.approve_payment(str(callback.from_user.id), payment_id)
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        raise

    user_chat_id = result["user_chat_id"]
    user_telegram_id = result["user_telegram_id"]
    text = (
        f"✅ پرداخت #{payment_id} تأیید شد.\n"
        f"👤 کاربر: {user_telegram_id}\n"
        f"💰 موجودی جدید کاربر: {format_toman(result['wallet_balance_toman'])}"
    )

    await edit_callback_message(message, text, parse_mode="HTML")

    notified = await notify_user_chat(
        message.bot,
        user_chat_id,
        wallet_recharged_message(result["wallet_balance_toman"]),
        reply_markup=buy_now_keyboard(),
    )
    if not notified:
        LOGGER.warning("Could not notify user %s after payment approval", user_telegram_id)

    await callback.answer("✅ تأیید شد")


@router.callback_query(F.data.startswith("admin:reject:"))
async def admin_reject(callback: CallbackQuery, api: UserManagerApiClient, bot_config: TelegramBotConfig) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    payment_id = int(callback.data.rsplit(":", 1)[1])
    await api.reject_payment(str(callback.from_user.id), payment_id)
    await edit_callback_message(message, f"❌ پرداخت #{payment_id} رد شد.")
    await callback.answer("❌ رد شد")
