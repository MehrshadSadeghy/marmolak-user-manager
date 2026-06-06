from aiogram import F, Router
from aiogram.types import CallbackQuery

from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.config import TelegramBotConfig
from vpn_core.telegram_bot.handlers.common import send_delivery
from vpn_core.telegram_bot.keyboards.main import admin_menu_keyboard, admin_services_keyboard
from vpn_core.telegram_bot.messages import PURPOSE_FA, format_toman

router = Router()


def _is_admin(callback: CallbackQuery, bot_config: TelegramBotConfig) -> bool:
    return str(callback.from_user.id) in bot_config.admin_chat_ids


@router.callback_query(F.data == "menu:admin")
async def menu_admin(callback: CallbackQuery, bot_config: TelegramBotConfig) -> None:
    message = callback.message
    if not message or not _is_admin(callback, bot_config):
        await callback.answer("⛔ دسترسی ادمین لازم است", show_alert=True)
        return
    await message.edit_text(
        "⚙️ <b>پنل مدیریت</b>\n\n👇 یک گزینه را انتخاب کن:",
        reply_markup=admin_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin:payments")
async def admin_payments(callback: CallbackQuery, api: UserManagerApiClient, bot_config: TelegramBotConfig) -> None:
    message = callback.message
    if not message or not _is_admin(callback, bot_config):
        await callback.answer("⛔ دسترسی ادمین لازم است", show_alert=True)
        return
    payments = await api.list_pending_payments(str(callback.from_user.id))
    if not payments:
        await message.edit_text(
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
        await message.edit_text(
            "⏳ <b>پرداخت‌های در انتظار</b>\n\n" + "\n".join(lines),
            reply_markup=admin_menu_keyboard(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "admin:services")
async def admin_services(callback: CallbackQuery, api: UserManagerApiClient, bot_config: TelegramBotConfig) -> None:
    message = callback.message
    if not message or not _is_admin(callback, bot_config):
        await callback.answer("⛔ دسترسی ادمین لازم است", show_alert=True)
        return
    services = await api.list_service_types_admin(str(callback.from_user.id))
    await message.edit_text(
        "🔧 <b>مدیریت انواع سرویس</b>\n\nروشن/خاموش کن:",
        reply_markup=admin_services_keyboard(services),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:toggle:"))
async def admin_toggle_service(callback: CallbackQuery, api: UserManagerApiClient, bot_config: TelegramBotConfig) -> None:
    message = callback.message
    if not message or not _is_admin(callback, bot_config):
        await callback.answer("⛔ دسترسی ادمین لازم است", show_alert=True)
        return
    _, _, action, slug = callback.data.split(":", 3)
    await api.toggle_service_type(str(callback.from_user.id), slug, action == "enable")
    services = await api.list_service_types_admin(str(callback.from_user.id))
    await message.edit_text(
        "🔧 <b>مدیریت انواع سرویس</b>\n\nروشن/خاموش کن:",
        reply_markup=admin_services_keyboard(services),
        parse_mode="HTML",
    )
    await callback.answer("✅ به‌روز شد")


@router.callback_query(F.data == "admin:plans")
async def admin_plans(callback: CallbackQuery, api: UserManagerApiClient, bot_config: TelegramBotConfig) -> None:
    message = callback.message
    if not message or not _is_admin(callback, bot_config):
        await callback.answer("⛔ دسترسی ادمین لازم است", show_alert=True)
        return
    plans = await api.list_plans_admin(str(callback.from_user.id))
    if not plans:
        await message.edit_text(
            "📋 پلنی تعریف نشده.",
            reply_markup=admin_menu_keyboard(),
        )
    else:
        lines = []
        for plan in plans:
            gb = plan["traffic_limit_bytes"] / (1024**3)
            lines.append(
                f"#{plan['id']} [{plan['service_type']}] {plan['name']} — "
                f"{gb:.0f}GB / {plan['duration_days']}روز — {format_toman(plan['price_toman'])}"
            )
        await message.edit_text(
            "📋 <b>لیست پلن‌ها</b>\n\n" + "\n".join(lines),
            reply_markup=admin_menu_keyboard(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:approve:"))
async def admin_approve(callback: CallbackQuery, api: UserManagerApiClient, bot_config: TelegramBotConfig) -> None:
    message = callback.message
    if not message or not _is_admin(callback, bot_config):
        await callback.answer("⛔ دسترسی ادمین لازم است", show_alert=True)
        return
    payment_id = int(callback.data.rsplit(":", 1)[1])
    result = await api.approve_payment(str(callback.from_user.id), payment_id)
    text = (
        f"✅ پرداخت #{payment_id} تأیید شد.\n"
        f"💰 موجودی: {format_toman(result['wallet_balance_toman'])}"
    )
    purchase = result.get("purchase")
    if purchase and purchase.get("delivery"):
        await message.edit_caption(text, parse_mode="HTML")
        await send_delivery(message, purchase["delivery"])
    else:
        await message.edit_caption(text, parse_mode="HTML")
    await callback.answer("✅ تأیید شد")


@router.callback_query(F.data.startswith("admin:reject:"))
async def admin_reject(callback: CallbackQuery, api: UserManagerApiClient, bot_config: TelegramBotConfig) -> None:
    message = callback.message
    if not message or not _is_admin(callback, bot_config):
        await callback.answer("⛔ دسترسی ادمین لازم است", show_alert=True)
        return
    payment_id = int(callback.data.rsplit(":", 1)[1])
    await api.reject_payment(str(callback.from_user.id), payment_id)
    await message.edit_caption(f"❌ پرداخت #{payment_id} رد شد.")
    await callback.answer("❌ رد شد")
