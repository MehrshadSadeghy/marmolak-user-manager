from aiogram import F, Router
from aiogram.types import CallbackQuery

from vpn_core.billing_domain.domain.payment_request import PaymentPurpose
from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.handlers.common import send_delivery
from vpn_core.telegram_bot.keyboards.main import (
    back_to_menu_keyboard,
    payment_methods_keyboard,
    plans_keyboard,
    services_keyboard,
)
from vpn_core.telegram_bot.messages import format_toman

router = Router()


@router.callback_query(F.data == "menu:buy")
async def menu_buy(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    services = await api.list_services()
    if not services:
        await message.edit_text(
            "😔 فعلاً سرویسی فعال نیست.\n"
            "📞 لطفاً با پشتیبانی تماس بگیرید.",
            reply_markup=back_to_menu_keyboard(),
        )
    else:
        await message.edit_text(
            "🛒 <b>خرید سرویس جدید</b>\n\n"
            "🔥 بهترین پلن‌ها با قیمت استثنایی!\n"
            "👇 نوع VPN مورد نظرت را انتخاب کن:",
            reply_markup=services_keyboard(services),
            parse_mode="HTML",
        )
    await callback.answer("🛒 انتخاب سرویس")


@router.callback_query(F.data.startswith("service:"))
async def select_service(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    service_type = callback.data.split(":", 1)[1]
    plans = await api.list_plans(service_type)
    if not plans:
        await message.edit_text(
            "😔 برای این سرویس پلنی تعریف نشده.\n"
            "📞 با پشتیبانی تماس بگیر.",
            reply_markup=back_to_menu_keyboard(),
        )
    else:
        await message.edit_text(
            "💎 <b>پلن مناسب خودت را انتخاب کن</b>\n\n"
            "⚡ فعال‌سازی آنی بعد از پرداخت\n"
            "🎁 هرچه زودتر بخری، زودتر وصل می‌شی!",
            reply_markup=plans_keyboard(plans, prefix="buy"),
            parse_mode="HTML",
        )
    await callback.answer("💎 انتخاب پلن")


@router.callback_query(F.data.startswith("buy:plan:"))
async def select_plan(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    plan_id = int(callback.data.rsplit(":", 1)[1])
    tg_id = str(callback.from_user.id)
    preview = await api.preview_purchase(tg_id, plan_id)
    if preview["sufficient_balance"]:
        result = await api.purchase(tg_id, plan_id)
        await message.edit_text(
            "🎉 <b>تبریک! خرید با موفقیت انجام شد</b>\n\n"
            f"💰 موجودی جدید: <b>{format_toman(result['wallet_balance_toman'])}</b>\n\n"
            "📩 کانفیگ سرویس در پیام بعدی ارسال می‌شود.",
            parse_mode="HTML",
        )
        await send_delivery(message, result.get("delivery"))
        await callback.answer("✅ خرید موفق!")
    else:
        methods = await api.list_payment_methods()
        if not methods:
            await message.edit_text(
                "😔 موجودی کافی نیست و روش پرداختی تنظیم نشده.\n"
                "💳 اول کیف پولت را شارژ کن یا با پشتیبانی تماس بگیر.",
                reply_markup=back_to_menu_keyboard(),
            )
        else:
            await message.edit_text(
                "💳 <b>موجودی کافی نیست — ولی نگران نباش!</b>\n\n"
                f"💰 مبلغ مورد نیاز: <b>{format_toman(preview['price_toman'])}</b>\n"
                f"👛 موجودی فعلی: <b>{format_toman(preview['wallet_balance_toman'])}</b>\n"
                f"📉 کسری: <b>{format_toman(preview['shortfall_toman'])}</b>\n\n"
                "👇 روش پرداخت را انتخاب کن و همین الان سرویس بگیر:",
                reply_markup=payment_methods_keyboard(methods, prefix=f"buy:{plan_id}"),
                parse_mode="HTML",
            )
        await callback.answer("💳 نیاز به پرداخت")


@router.callback_query(F.data.regexp(r"^buy:\d+:pay:\d+$"))
async def buy_with_payment(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    _, plan_id, _, method_id = callback.data.split(":")
    tg_id = str(callback.from_user.id)
    payment = await api.initiate_payment(
        {
            "telegram_id": tg_id,
            "purpose": PaymentPurpose.purchase.value,
            "amount_toman": 0,
            "plan_id": int(plan_id),
            "payment_method_id": int(method_id),
        }
    )
    methods = await api.list_payment_methods()
    method = next(m for m in methods if m["id"] == int(method_id))
    support = await api.get_support()
    instructions = support.get("payment_instructions") or ""
    await message.edit_text(
        "💸 <b>درخواست پرداخت ثبت شد</b>\n\n"
        f"💰 مبلغ: <b>{format_toman(payment['payment_request']['amount_toman'])}</b>\n\n"
        f"🏦 <b>{method['name']}</b>\n"
        f"{method['instructions']}\n\n"
        f"{instructions}\n\n"
        "📸 بعد از پرداخت، <b>عکس رسید</b> را همینجا بفرست.\n"
        "⏳ بعد از تأیید ادمین، سرویس فوراً فعال می‌شود!",
        parse_mode="HTML",
    )
    await callback.answer("📸 منتظر رسید")
