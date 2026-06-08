import httpx
from aiogram import F, Router
from aiogram.types import CallbackQuery

from vpn_core.billing_domain.domain.payment_request import PaymentPurpose
from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.handlers.common import (
    resolve_purchase_delivery,
    send_delivery,
    send_delivery_to_chat,
)
from vpn_core.telegram_bot.keyboards.main import (
    back_to_menu_keyboard,
    buy_now_keyboard,
    payment_methods_keyboard,
    plans_keyboard,
    renew_services_keyboard,
    user_services_keyboard,
)
from vpn_core.telegram_bot.messages import format_payment_method_display, format_toman, status_label_fa

router = Router()


@router.callback_query(F.data == "menu:services")
async def menu_services(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    services = await api.list_user_services(str(callback.from_user.id))
    if not services:
        await message.edit_text(
            "📦 هنوز سرویسی نداری!\n\n"
            "🚀 همین الان اولین سرویس VPNت را بخر:\n"
            "⚡ سرعت بالا · 🔒 امنیت کامل · 💎 قیمت عالی\n\n"
            "👇 روی دکمه زیر بزن و شروع کن:",
            reply_markup=buy_now_keyboard(),
            parse_mode="HTML",
        )
    else:
        lines = []
        for item in services:
            status = status_label_fa(item["status_label"])
            lines.append(
                f"🔹 <b>#{item['subscription_id']}</b> {item['service_type']} — {status}\n"
                f"📋 پلن: {item['plan_name'] or '—'}\n"
                f"⏳ باقی‌مانده: {item['remaining_days']} روز · 📊 {item['remaining_data_label']}"
            )
        await message.edit_text(
            "📦 <b>سرویس‌های من</b>\n\n"
            + "\n\n".join(lines)
            + "\n\n👇 برای دریافت فایل .ovpn، دکمه مربوطه را بزن:",
            reply_markup=user_services_keyboard(services),
            parse_mode="HTML",
        )
    await callback.answer("📦 سرویس‌های شما")


@router.callback_query(F.data.startswith("download:sub:"))
async def download_subscription_config(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    subscription_id = int(callback.data.rsplit(":", 1)[1])
    tg_id = str(callback.from_user.id)
    try:
        delivery = await api.get_subscription_delivery(tg_id, subscription_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            await callback.answer(
                "❌ فایل کانفیگ یافت نشد. با پشتیبانی تماس بگیر.",
                show_alert=True,
            )
            return
        raise
    await send_delivery_to_chat(message.bot, tg_id, delivery, reply_markup=buy_now_keyboard())
    await callback.answer("📥 فایل ارسال شد")


@router.callback_query(F.data.startswith("download:config:"))
async def download_config_by_id(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    config_id = callback.data.rsplit(":", 1)[1]
    tg_id = str(callback.from_user.id)
    try:
        delivery = await api.get_openvpn_config_delivery(tg_id, config_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            await callback.answer(
                "❌ فایل کانفیگ یافت نشد. با پشتیبانی تماس بگیر.",
                show_alert=True,
            )
            return
        raise
    await send_delivery_to_chat(message.bot, tg_id, delivery, reply_markup=buy_now_keyboard())
    await callback.answer("📥 فایل ارسال شد")


@router.callback_query(F.data == "menu:renew")
async def menu_renew(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    services = await api.list_user_services(str(callback.from_user.id))
    if not services:
        await message.edit_text(
            "😔 سرویسی برای تمدید نداری.\n\n"
            "🛒 اول یک سرویس بخر، بعد هر وقت خواستی تمدیدش کن!",
            reply_markup=buy_now_keyboard(),
            parse_mode="HTML",
        )
    else:
        await message.edit_text(
            "🔄 <b>تمدید سرویس</b>\n\n"
            "👇 سرویسی که می‌خواهی تمدید کنی را انتخاب کن:",
            reply_markup=renew_services_keyboard(services),
            parse_mode="HTML",
        )
    await callback.answer("🔄 تمدید")


@router.callback_query(F.data.startswith("renew:sub:"))
async def renew_subscription(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    subscription_id = int(callback.data.rsplit(":", 1)[1])
    tg_id = str(callback.from_user.id)
    services = await api.list_user_services(tg_id)
    selected = next(s for s in services if s["subscription_id"] == subscription_id)
    if selected["is_active"]:
        await message.edit_text(
            f"✅ سرویس <b>#{subscription_id}</b> فعال است.\n\n"
            f"⏳ زمان باقی‌مانده: <b>{selected['remaining_days']} روز</b>\n"
            f"📊 حجم باقی‌مانده: <b>{selected['remaining_data_label']}</b>\n\n"
            "🎉 نیازی به تمدید نیست — از VPN لذت ببر!",
            parse_mode="HTML",
        )
        await callback.answer("✅ سرویس فعال است")
        return
    plans = await api.list_plans(selected["service_type"])
    if not plans:
        await message.edit_text(
            "😔 پلنی برای تمدید موجود نیست.\n📞 با پشتیبانی تماس بگیر.",
            reply_markup=buy_now_keyboard(),
        )
    else:
        await message.edit_text(
            "🔄 <b>تمدید سرویس</b>\n\n"
            "💎 پلن تمدید را انتخاب کن و دوباره وصل شو:",
            reply_markup=plans_keyboard(plans, prefix=f"renew:{subscription_id}"),
            parse_mode="HTML",
        )
    await callback.answer("💎 انتخاب پلن")


@router.callback_query(F.data.regexp(r"^renew:\d+:plan:\d+$"))
async def renew_plan(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    _, subscription_id, _, plan_id = callback.data.split(":")
    tg_id = str(callback.from_user.id)
    preview = await api.preview_purchase(tg_id, int(plan_id))
    if preview["sufficient_balance"]:
        result = await api.renew(tg_id, int(subscription_id), int(plan_id))
        await message.edit_text(
            "🎉 <b>تمدید با موفقیت انجام شد!</b>\n\n"
            f"💰 موجودی جدید: <b>{format_toman(result['wallet_balance_toman'])}</b>\n\n"
            "📩 کانفیگ در پیام بعدی ارسال می‌شود.",
            parse_mode="HTML",
        )
        delivery = await resolve_purchase_delivery(api, tg_id, result)
        await send_delivery(message, delivery)
        await callback.answer("✅ تمدید موفق!")
    else:
        methods = await api.list_payment_methods()
        if not methods:
            await message.edit_text(
                "😔 موجودی کافی نیست.\n💳 کیف پولت را شارژ کن یا با پشتیبانی تماس بگیر.",
                reply_markup=buy_now_keyboard(),
            )
        else:
            await message.edit_text(
                "💳 <b>موجودی برای تمدید کافی نیست</b>\n\n"
                "👇 روش پرداخت را انتخاب کن:",
                reply_markup=payment_methods_keyboard(
                    methods,
                    prefix=f"renewpay:{subscription_id}:{plan_id}",
                ),
                parse_mode="HTML",
            )
        await callback.answer("💳 نیاز به پرداخت")


@router.callback_query(F.data.regexp(r"^renewpay:\d+:\d+:pay:\d+$"))
async def renew_with_payment(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    _, subscription_id, plan_id, _, method_id = callback.data.split(":")
    tg_id = str(callback.from_user.id)
    payment = await api.initiate_payment(
        {
            "telegram_id": tg_id,
            "purpose": PaymentPurpose.renewal.value,
            "amount_toman": 0,
            "plan_id": int(plan_id),
            "subscription_id": int(subscription_id),
            "payment_method_id": int(method_id),
        }
    )
    methods = await api.list_payment_methods()
    method = next(m for m in methods if m["id"] == int(method_id))
    await message.edit_text(
        "💸 <b>درخواست پرداخت تمدید ثبت شد</b>\n\n"
        f"💰 مبلغ: <b>{format_toman(payment['payment_request']['amount_toman'])}</b>\n\n"
        f"{format_payment_method_display(method)}\n\n"
        "📸 عکس رسید را همینجا بفرست.\n"
        "⏳ بعد از تأیید، سرویس دوباره فعال می‌شود!",
        parse_mode="HTML",
    )
    await callback.answer("📸 منتظر رسید")
