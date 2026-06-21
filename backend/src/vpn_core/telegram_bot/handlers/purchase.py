from aiogram import F, Router
from aiogram.types import CallbackQuery

from vpn_core.billing_domain.domain.payment_request import PaymentPurpose
from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.handlers.common import resolve_purchase_delivery, send_delivery, edit_callback_message
from vpn_core.telegram_bot.keyboards.main import (
    back_to_menu_keyboard,
    openvpn_servers_purchase_keyboard,
    payment_methods_keyboard,
    plans_keyboard,
    services_keyboard,
)
from vpn_core.telegram_bot.messages import format_payment_method_display, format_toman

router = Router()


@router.callback_query(F.data == "menu:buy")
async def menu_buy(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    services = await api.list_services()
    if not services:
        await edit_callback_message(message, 
            "😔 فعلاً سرویسی فعال نیست.\n"
            "📞 لطفاً با پشتیبانی تماس بگیرید.",
            reply_markup=back_to_menu_keyboard(),
        )
    else:
        await edit_callback_message(message, 
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
    tg_id = str(callback.from_user.id)

    if service_type == "openvpn":
        servers = await api.list_openvpn_servers()
        if not servers:
            await edit_callback_message(message, 
                "😔 سرور OpenVPN فعالی موجود نیست.\n"
                "📞 با پشتیبانی تماس بگیر.",
                reply_markup=back_to_menu_keyboard(),
            )
        elif all(server.get("is_full") for server in servers):
            await edit_callback_message(message, 
                "😔 همه سرورهای OpenVPN در حال حاضر پر هستند.\n"
                "⏳ لطفاً بعداً دوباره تلاش کن یا با پشتیبانی تماس بگیر.",
                reply_markup=back_to_menu_keyboard(),
            )
        else:
            await edit_callback_message(message, 
                "🖥 <b>انتخاب سرور OpenVPN</b>\n\n"
                "🟢 سرورهای آزاد قابل خرید هستند.\n"
                "🔴 سرورهای پر موقتاً غیرفعال‌اند.\n\n"
                "👇 سرور مورد نظرت را انتخاب کن:",
                reply_markup=openvpn_servers_purchase_keyboard(servers),
                parse_mode="HTML",
            )
        await callback.answer("🖥 انتخاب سرور")
        return

    plans = await api.list_plans(service_type, telegram_id=tg_id)
    if not plans:
        await edit_callback_message(message, 
            "😔 برای این سرویس پلنی تعریف نشده.\n"
            "📞 با پشتیبانی تماس بگیر.",
            reply_markup=back_to_menu_keyboard(),
        )
    else:
        await edit_callback_message(message, 
            "💎 <b>پلن مناسب خودت را انتخاب کن</b>\n\n"
            "⚡ فعال‌سازی آنی بعد از پرداخت\n"
            "🎁 هرچه زودتر بخری، زودتر وصل می‌شی!",
            reply_markup=plans_keyboard(plans, prefix="buy"),
            parse_mode="HTML",
        )
    await callback.answer("💎 انتخاب پلن")


@router.callback_query(F.data.startswith("buy:server-full:"))
async def server_full_alert(callback: CallbackQuery) -> None:
    await callback.answer("این سرور پر است. لطفاً سرور دیگری انتخاب کن.", show_alert=True)


@router.callback_query(F.data.startswith("buy:server:"))
async def select_openvpn_server(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    server_id = int(callback.data.rsplit(":", 1)[1])
    tg_id = str(callback.from_user.id)
    plans = await api.list_plans("openvpn", telegram_id=tg_id)
    if not plans:
        await edit_callback_message(message, 
            "😔 برای OpenVPN پلنی تعریف نشده.\n"
            "📞 با پشتیبانی تماس بگیر.",
            reply_markup=back_to_menu_keyboard(),
        )
    else:
        await edit_callback_message(message, 
            "💎 <b>پلن مناسب خودت را انتخاب کن</b>\n\n"
            "⚡ فعال‌سازی آنی بعد از پرداخت\n"
            "🎁 هرچه زودتر بخری، زودتر وصل می‌شی!",
            reply_markup=plans_keyboard(
                plans,
                prefix=f"buy:sv:{server_id}",
                back_callback="service:openvpn",
            ),
            parse_mode="HTML",
        )
    await callback.answer("💎 انتخاب پلن")


async def _complete_purchase(
    callback: CallbackQuery,
    api: UserManagerApiClient,
    *,
    plan_id: int,
    server_id: int | None = None,
) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    tg_id = str(callback.from_user.id)
    preview = await api.preview_purchase(tg_id, plan_id, server_id=server_id)
    if preview["sufficient_balance"]:
        result = await api.purchase(tg_id, plan_id, server_id=server_id)
        await edit_callback_message(message, 
            "🎉 <b>تبریک! خرید با موفقیت انجام شد</b>\n\n"
            f"💰 موجودی جدید: <b>{format_toman(result['wallet_balance_toman'])}</b>\n\n"
            "📩 کانفیگ سرویس در پیام بعدی ارسال می‌شود.",
            parse_mode="HTML",
        )
        delivery = await resolve_purchase_delivery(api, tg_id, result)
        await send_delivery(message, delivery)
        if not delivery:
            await message.answer(
                "⚠️ سرویس فعال شد اما ارسال خودکار کانفیگ ناموفق بود.\n"
                "📦 از منوی «سرویس‌های من» می‌توانی فایل .ovpn را دریافت کنی.",
                reply_markup=back_to_menu_keyboard(),
                parse_mode="HTML",
            )
        await callback.answer("✅ خرید موفق!")
    else:
        methods = await api.list_payment_methods()
        if not methods:
            await edit_callback_message(message, 
                "😔 موجودی کافی نیست و روش پرداختی تنظیم نشده.\n"
                "💳 اول کیف پولت را شارژ کن یا با پشتیبانی تماس بگیر.",
                reply_markup=back_to_menu_keyboard(),
            )
        else:
            prefix = (
                f"buy:sv:{server_id}:plan:{plan_id}"
                if server_id is not None
                else f"buy:{plan_id}"
            )
            await edit_callback_message(message, 
                "💳 <b>موجودی کافی نیست</b>\n\n"
                f"💰 مبلغ پلن: <b>{format_toman(preview['price_toman'])}</b>\n"
                f"👛 موجودی فعلی: <b>{format_toman(preview['wallet_balance_toman'])}</b>\n"
                f"📉 کسری: <b>{format_toman(preview['shortfall_toman'])}</b>\n\n"
                "👇 ابتدا کیف پول را شارژ کن. بعد از تأیید ادمین، دوباره همین پلن را بخر.",
                reply_markup=payment_methods_keyboard(methods, prefix=prefix),
                parse_mode="HTML",
            )
        await callback.answer("💳 نیاز به پرداخت")


@router.callback_query(F.data.startswith("buy:sv:") & F.data.contains(":plan:"))
async def select_plan_with_server(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    parts = callback.data.split(":")
    server_id = int(parts[2])
    plan_id = int(parts[4])
    await _complete_purchase(callback, api, plan_id=plan_id, server_id=server_id)


@router.callback_query(F.data.startswith("buy:plan:"))
async def select_plan(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    plan_id = int(callback.data.rsplit(":", 1)[1])
    await _complete_purchase(callback, api, plan_id=plan_id)


@router.callback_query(F.data.regexp(r"^buy:sv:\d+:plan:\d+:pay:\d+$"))
async def buy_with_payment_openvpn(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    _, _, server_id, _, plan_id, _, method_id = callback.data.split(":")
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
    await edit_callback_message(message, 
        "💸 <b>درخواست شارژ کیف پول ثبت شد</b>\n\n"
        f"💰 مبلغ: <b>{format_toman(payment['payment_request']['amount_toman'])}</b>\n\n"
        f"{format_payment_method_display(method)}\n\n"
        f"{instructions}\n\n"
        "📸 بعد از پرداخت، <b>عکس رسید</b> را همینجا بفرست.\n"
        "⏳ بعد از تأیید ادمین، موجودی شارژ می‌شود.\n"
        f"🛒 سپس دوباره سرور #{server_id} و همین پلن را انتخاب کن و خرید را تکمیل کن.",
        parse_mode="HTML",
    )
    await callback.answer("📸 منتظر رسید")


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
    await edit_callback_message(message, 
        "💸 <b>درخواست شارژ کیف پول ثبت شد</b>\n\n"
        f"💰 مبلغ: <b>{format_toman(payment['payment_request']['amount_toman'])}</b>\n\n"
        f"{format_payment_method_display(method)}\n\n"
        f"{instructions}\n\n"
        "📸 بعد از پرداخت، <b>عکس رسید</b> را همینجا بفرست.\n"
        "⏳ بعد از تأیید ادمین، موجودی شارژ می‌شود.\n"
        "🛒 سپس دوباره همین پلن را انتخاب کن و خرید را تکمیل کن.",
        parse_mode="HTML",
    )
    await callback.answer("📸 منتظر رسید")
