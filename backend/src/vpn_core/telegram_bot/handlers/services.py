import httpx
from aiogram import F, Router
from aiogram.types import CallbackQuery

from vpn_core.billing_domain.domain.payment_request import PaymentPurpose
from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.handlers.common import (
    edit_callback_message,
    resolve_purchase_delivery,
    send_delivery,
    send_openvpn_delivery_to_chat,
)
from vpn_core.telegram_bot.keyboards.main import (
    back_to_menu_keyboard,
    buy_now_keyboard,
    payment_methods_keyboard,
    plans_keyboard,
    renew_services_keyboard,
    user_services_keyboard,
    user_subscription_manage_keyboard,
)
from vpn_core.telegram_bot.messages import format_payment_method_display, format_toman, status_label_fa

router = Router()


@router.callback_query(F.data == "menu:services")
async def menu_services(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    services_payload = await api.list_user_services(str(callback.from_user.id))
    services = services_payload.get("services") or []
    subscription_url = services_payload.get("subscription_url")
    if not services:
        await edit_callback_message(message, 
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
        await edit_callback_message(message, 
            "📦 <b>سرویس‌های من</b>\n\n"
            + "\n\n".join(lines)
            + "\n\n👇 برای دریافت کانفیگ (فایل .ovpn، لینک V2Ray، یا لینک اشتراک Hiddify/Happ)، دکمه مربوطه را بزن:",
            reply_markup=user_services_keyboard(services, subscription_url=subscription_url),
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
    await send_openvpn_delivery_to_chat(message.bot, tg_id, delivery, reply_markup=buy_now_keyboard())
    await callback.answer("📥 فایل ارسال شد")


@router.callback_query(F.data.startswith("credentials:view:"))
async def view_openvpn_credentials(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    config_id = callback.data.rsplit(":", 1)[1]
    tg_id = str(callback.from_user.id)
    try:
        delivery = await api.get_openvpn_credential_view(tg_id, config_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            await callback.answer("❌ اطلاعات کانفیگ یافت نشد.", show_alert=True)
            return
        raise
    await send_openvpn_delivery_to_chat(
        message.bot,
        tg_id,
        delivery,
        reply_markup=buy_now_keyboard(),
        view_only=True,
    )
    await callback.answer("ℹ️ اطلاعات ارسال شد")


@router.callback_query(F.data.startswith("credentials:rotate:"))
async def rotate_openvpn_credentials(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    config_id = callback.data.rsplit(":", 1)[1]
    tg_id = str(callback.from_user.id)
    try:
        delivery = await api.rotate_openvpn_credentials(tg_id, config_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 400:
            await callback.answer(
                "این کانفیگ فقط با گواهی (certificate) کار می‌کند و رمز ندارد.",
                show_alert=True,
            )
            return
        if exc.response.status_code == 404:
            await callback.answer("❌ کانفیگ یافت نشد.", show_alert=True)
            return
        raise
    await send_openvpn_delivery_to_chat(message.bot, tg_id, delivery, reply_markup=buy_now_keyboard())
    await callback.answer("🔑 رمز جدید ارسال شد")


@router.callback_query(F.data.startswith("credentials:migrate:"))
async def migrate_openvpn_credentials(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    config_id = callback.data.rsplit(":", 1)[1]
    tg_id = str(callback.from_user.id)
    try:
        delivery = await api.migrate_openvpn_credentials(tg_id, config_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 400:
            await callback.answer(
                "این گزینه برای کانفیگ شما فعال نیست. سرور باید در حالت dual باشد.",
                show_alert=True,
            )
            return
        if exc.response.status_code == 404:
            await callback.answer("❌ کانفیگ یافت نشد.", show_alert=True)
            return
        raise
    await send_openvpn_delivery_to_chat(message.bot, tg_id, delivery, reply_markup=buy_now_keyboard())
    await callback.answer("🔐 نام کاربری و رمز ارسال شد")


@router.callback_query(F.data.startswith("credentials:finalize:"))
async def finalize_openvpn_auth_migration(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    config_id = callback.data.rsplit(":", 1)[1]
    tg_id = str(callback.from_user.id)
    try:
        delivery = await api.finalize_openvpn_auth_migration(tg_id, config_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 400:
            await callback.answer(
                "هنوز زمان حذف گواهی قدیمی نرسیده. چند روز دیگر دوباره امتحان کن.",
                show_alert=True,
            )
            return
        if exc.response.status_code == 404:
            await callback.answer("❌ کانفیگ یافت نشد.", show_alert=True)
            return
        raise
    await send_openvpn_delivery_to_chat(message.bot, tg_id, delivery, reply_markup=buy_now_keyboard())
    await callback.answer("✅ کانفیگ جدید ارسال شد")


@router.callback_query(F.data == "subscription:manage")
async def manage_client_subscription(callback: CallbackQuery) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    await edit_callback_message(
        message,
        "📲 <b>مدیریت اشتراک V2Ray</b>\n\n"
        "با لینک اشتراک، برنامه‌های Hiddify، Happ، v2rayNG و Streisand "
        "به‌صورت خودکار کانفیگ‌ها را دریافت و به‌روز می‌کنند.\n\n"
        "👇 یکی از گزینه‌ها را انتخاب کن:",
        reply_markup=user_subscription_manage_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "subscription:help")
async def subscription_help(callback: CallbackQuery) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    await edit_callback_message(
        message,
        "📖 <b>راهنمای Hiddify / Happ</b>\n\n"
        "1️⃣ از منوی «دریافت لینک اشتراک»، URL را کپی کن.\n"
        "2️⃣ در Hiddify/Happ برو به Add Subscription / افزودن اشتراک.\n"
        "3️⃣ لینک را Paste کن و ذخیره کن.\n"
        "4️⃣ برنامه خودکار کانفیگ‌ها را sync می‌کند.\n\n"
        "💡 اگر پروتکل یا پورت سرور عوض شد، همین لینk را دوباره sync کن.",
        reply_markup=user_subscription_manage_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "subscription:url")
async def send_client_subscription_url(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    tg_id = str(callback.from_user.id)
    try:
        payload = await api.get_client_subscription_url(tg_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            await callback.answer("❌ لینک اشتراک یافت نشد.", show_alert=True)
            return
        raise
    subscription_url = payload["subscription_url"]
    await message.answer(
        "📲 <b>لینک اشتراک V2Ray</b>\n\n"
        "این لینک را در Hiddify، Happ، v2rayNG یا Streisand به‌عنوان "
        "<b>Subscription URL</b> اضافه کن.\n"
        "برنامه به‌صورت خودکار کانفیگ‌ها را دریافت و به‌روز می‌کند.\n\n"
        f"🔗 <code>{subscription_url}</code>",
        parse_mode="HTML",
    )
    await callback.answer("📲 لینک اشتراک ارسال شد")


@router.callback_query(F.data.startswith("download:v2ray:"))
async def download_v2ray_config_by_id(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    config_id = callback.data.rsplit(":", 1)[1]
    tg_id = str(callback.from_user.id)
    try:
        delivery = await api.get_v2ray_config_delivery(tg_id, config_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            await callback.answer(
                "❌ لینک کانفیگ یافت نشد. با پشتیبانی تماس بگیر.",
                show_alert=True,
            )
            return
        raise
    await send_openvpn_delivery_to_chat(message.bot, tg_id, delivery, reply_markup=buy_now_keyboard())
    await callback.answer("🔗 لینک ارسال شد")


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
    await send_openvpn_delivery_to_chat(message.bot, tg_id, delivery, reply_markup=buy_now_keyboard())
    await callback.answer("📥 فایل ارسال شد")


@router.callback_query(F.data == "menu:renew")
async def menu_renew(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    services_payload = await api.list_user_services(str(callback.from_user.id))
    services = services_payload.get("services") or []
    if not services:
        await edit_callback_message(message, 
            "😔 سرویسی برای تمدید نداری.\n\n"
            "🛒 اول یک سرویس بخر، بعد هر وقت خواستی تمدیدش کن!",
            reply_markup=buy_now_keyboard(),
            parse_mode="HTML",
        )
    else:
        await edit_callback_message(message, 
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
    services_payload = await api.list_user_services(tg_id)
    services = services_payload.get("services") or []
    selected = next(s for s in services if s["subscription_id"] == subscription_id)
    if selected["is_active"]:
        await edit_callback_message(message, 
            f"✅ سرویس <b>#{subscription_id}</b> فعال است.\n\n"
            f"⏳ زمان باقی‌مانده: <b>{selected['remaining_days']} روز</b>\n"
            f"📊 حجم باقی‌مانده: <b>{selected['remaining_data_label']}</b>\n\n"
            "🎉 نیازی به تمدید نیست — از VPN لذت ببر!",
            parse_mode="HTML",
        )
        await callback.answer("✅ سرویس فعال است")
        return
    plans = await api.list_plans(selected["service_type"], telegram_id=tg_id)
    if not plans:
        await edit_callback_message(message, 
            "😔 پلنی برای تمدید موجود نیست.\n📞 با پشتیبانی تماس بگیر.",
            reply_markup=buy_now_keyboard(),
        )
    else:
        await edit_callback_message(message, 
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
        await edit_callback_message(message, 
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
            await edit_callback_message(message, 
                "😔 موجودی کافی نیست.\n💳 کیف پولت را شارژ کن یا با پشتیبانی تماس بگیر.",
                reply_markup=buy_now_keyboard(),
            )
        else:
            await edit_callback_message(message, 
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
    await edit_callback_message(message, 
        "💸 <b>درخواست پرداخت تمدید ثبت شد</b>\n\n"
        f"💰 مبلغ: <b>{format_toman(payment['payment_request']['amount_toman'])}</b>\n\n"
        f"{format_payment_method_display(method)}\n\n"
        "📸 عکس رسید را همینجا بفرست.\n"
        "⏳ بعد از تأیید، سرویس دوباره فعال می‌شود!",
        parse_mode="HTML",
    )
    await callback.answer("📸 منتظر رسید")
