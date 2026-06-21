import httpx
from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from vpn_core.pasarguard_panel_domain.utils.token import parse_subscription_token
from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.config import TelegramBotConfig
from vpn_core.telegram_bot.handlers.common import (
    edit_callback_message,
    ensure_user,
    send_delivery_to_chat,
    telegram_id,
)
from vpn_core.telegram_bot.keyboards.main import (
    back_to_menu_keyboard,
    buy_now_keyboard,
    main_menu_keyboard,
    pasarguard_panel_keyboard,
)
from vpn_core.telegram_bot.states import UserFlow
from vpn_core.telegram_bot.utils.qr import send_subscription_qr

router = Router()


def _format_panel_info(info: dict) -> str:
    return (
        "✅ <b>پنل پاسارگارد متصل شد</b>\n\n"
        f"👤 نام کاربری: <code>{info.get('username') or '—'}</code>\n"
        f"📌 وضعیت: <b>{info.get('status') or '—'}</b>\n"
        f"📶 حجم: <b>{info.get('used_traffic_label')}</b> / <b>{info.get('data_limit_label')}</b>\n"
        f"📅 انقضا: <b>{info.get('expire_at')}</b> ({info.get('days_left')} روز)\n\n"
        f"🔗 <b>لینک اشتراک:</b>\n<code>{info.get('subscription_url')}</code>\n\n"
        "👇 برای افزودن به اپلیکیشن، دکمه «افزودن پنل پاسارگارد» را بزن.\n"
        "📥 برای دریافت فایل <code>.ovpn</code> از سرویس OpenVPN همین ربات، دکمه مربوطه را انتخاب کن."
    )


async def _panel_settings(api: UserManagerApiClient) -> dict:
    try:
        return await api.get_pasarguard_panel_settings()
    except Exception:
        return {"enabled": False, "webapp_url": None}


async def _show_connection(
    message: Message,
    *,
    connection: dict,
    settings: dict,
    bot_config: TelegramBotConfig,
) -> None:
    info = connection.get("info")
    if not info:
        await message.answer(
            "⚠️ اتصال پنل پاسارگارد یافت نشد یا منقضی شده است.\n"
            "لینک اشتراک خود را دوباره بفرست.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    await message.answer(
        _format_panel_info(info),
        reply_markup=pasarguard_panel_keyboard(
            webapp_url=settings.get("webapp_url"),
            apps=connection.get("apps"),
        ),
        parse_mode="HTML",
    )
    await send_subscription_qr(
        message,
        info["subscription_url"],
        info.get("username") or "user",
    )


async def _connect_and_show(
    message: Message,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
    subscription_input: str,
) -> bool:
    settings = await _panel_settings(api)
    if not settings.get("enabled"):
        await message.answer(
            "⚠️ اتصال پنل پاسارگارد هنوز توسط مدیر فعال نشده است.",
            reply_markup=back_to_menu_keyboard(),
        )
        return False

    tg_id = telegram_id(message)
    try:
        connection = await api.connect_pasarguard_panel(tg_id, subscription_input)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            await message.answer(
                "❌ اشتراک پاسارگارد پیدا نشد.\n"
                "لینک یا توکن اشتراک را بررسی کن.",
                reply_markup=back_to_menu_keyboard(),
            )
            return False
        if exc.response.status_code in (400, 502, 503):
            detail = exc.response.text
            try:
                detail = exc.response.json().get("detail", detail)
            except Exception:
                pass
            await message.answer(f"⚠️ خطا: {detail}", reply_markup=back_to_menu_keyboard())
            return False
        raise

    await _show_connection(message, connection=connection, settings=settings, bot_config=bot_config)
    return True


@router.callback_query(F.data == "menu:pasarguard")
async def menu_pasarguard(
    callback: CallbackQuery,
    state: FSMContext,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return

    settings = await _panel_settings(api)
    if not settings.get("enabled"):
        await edit_callback_message(
            message,
            "⚠️ اتصال پنل پاسارگارد هنوز توسط مدیر فعال نشده است.",
            reply_markup=back_to_menu_keyboard(),
        )
        await callback.answer()
        return

    tg_id = str(callback.from_user.id)
    try:
        connection = await api.get_pasarguard_connection(tg_id)
        await edit_callback_message(
            message,
            _format_panel_info(connection["info"]),
            reply_markup=pasarguard_panel_keyboard(
                webapp_url=settings.get("webapp_url"),
                apps=connection.get("apps"),
            ),
            parse_mode="HTML",
        )
        await send_subscription_qr(
            message,
            connection["info"]["subscription_url"],
            connection["info"].get("username") or "user",
        )
        await callback.answer("🔗 پنل پاسارگارد")
        return
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code != 404:
            raise

    await state.set_state(UserFlow.waiting_pasarguard_link)
    text = (
        "🔗 <b>افزودن پنل پاسارگارد</b>\n\n"
        "لینک یا توکن اشتراک پاسارگارد خود را بفرست.\n"
        "مثال:\n"
        "<code>https://panel.example.com/sub/TOKEN</code>\n\n"
        "بعد از اتصال می‌توانی:\n"
        "• پنل را در اپلیکیشن VPN اضافه کنی\n"
        "• فایل <code>.ovpn</code> را از همین ربات دریافت کنی"
    )
    keyboard = back_to_menu_keyboard()
    if settings.get("webapp_url"):
        keyboard = pasarguard_panel_keyboard(webapp_url=settings.get("webapp_url"))
    await edit_callback_message(message, text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.message(UserFlow.waiting_pasarguard_link, F.text)
async def receive_pasarguard_link(
    message: Message,
    state: FSMContext,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    await state.clear()
    await _connect_and_show(message, api, bot_config, message.text or "")


@router.callback_query(F.data == "pasarguard:openvpn")
async def pasarguard_openvpn_delivery(
    callback: CallbackQuery,
    api: UserManagerApiClient,
) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return

    tg_id = str(callback.from_user.id)
    try:
        delivery = await api.get_pasarguard_openvpn_delivery(tg_id)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            await callback.answer(
                "فایل OpenVPN برای حساب شما موجود نیست. ابتدا سرویس OpenVPN بخر.",
                show_alert=True,
            )
            return
        raise

    await send_delivery_to_chat(message.bot, tg_id, delivery, reply_markup=buy_now_keyboard())
    await callback.answer("📥 فایل OpenVPN ارسال شد")


@router.message(CommandStart(deep_link=True))
async def cmd_start_with_panel_link(
    message: Message,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2:
        return

    token = parse_subscription_token(args[1])
    if not token:
        return

    settings = await _panel_settings(api)
    if not settings.get("enabled"):
        return

    await ensure_user(api, message)
    connected = await _connect_and_show(message, api, bot_config, args[1])
    if connected:
        is_admin = telegram_id(message) in bot_config.admin_chat_ids
        await message.answer(
            "🏠 از منوی زیر ادامه بده:",
            reply_markup=main_menu_keyboard(
                is_admin,
                pasarguard_enabled=True,
            ),
        )
