import logging

import httpx
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardMarkup, Message

from vpn_core.telegram_bot.config import TelegramBotConfig

from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.keyboards.main import buy_now_keyboard
from vpn_core.openvpn_sync.services.openvpn_credential_delivery_service import (
    OpenVpnCredentialDeliveryService,
)

LOGGER = logging.getLogger(__name__)


def telegram_id(message: Message) -> str:
    return str(message.from_user.id)


def chat_id(message: Message) -> str:
    return str(message.chat.id)


def username(message: Message) -> str | None:
    return message.from_user.username


async def ensure_user(api: UserManagerApiClient, message: Message) -> dict:
    return await api.register_user(telegram_id(message), chat_id(message), username(message))


def _is_media_message(message: Message) -> bool:
    return bool(message.photo or message.document or message.video or message.animation)


async def edit_callback_message(
    message: Message,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
) -> None:
    """Edit inline-keyboard menu text for both plain and media (photo) messages."""
    try:
        if _is_media_message(message):
            await message.edit_caption(
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        else:
            await message.edit_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
    except TelegramBadRequest as exc:
        error = str(exc).lower()
        if "message is not modified" in error:
            return
        if "there is no text in the message to edit" in error or "message can't be edited" in error:
            await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
        raise


async def answer_callback(callback: CallbackQuery, text: str | None = None, *, show_alert: bool = False) -> None:
    try:
        await callback.answer(text, show_alert=show_alert)
    except TelegramBadRequest:
        pass


async def mark_callback_answered(data: dict) -> None:
    mark = data.get("mark_callback_answered")
    if callable(mark):
        await mark()


async def notify_user_chat(
    bot,
    chat_id: str | int,
    text: str,
    *,
    reply_markup=None,
    parse_mode: str = "HTML",
) -> bool:
    try:
        await bot.send_message(int(chat_id), text, reply_markup=reply_markup, parse_mode=parse_mode)
        return True
    except Exception:
        LOGGER.exception("Failed to send notification to chat_id=%s", chat_id)
        return False


async def send_delivery(message: Message, delivery: dict) -> None:
    await send_openvpn_delivery_to_chat(
        message.bot,
        message.chat.id,
        delivery,
        reply_markup=buy_now_keyboard(),
    )


async def send_openvpn_delivery_to_chat(
    bot,
    chat_id: str | int,
    delivery: dict,
    *,
    reply_markup=None,
    view_only: bool = False,
) -> bool:
    if not delivery:
        return False
    try:
        if delivery.get("service_type") == "openvpn" and (
            OpenVpnCredentialDeliveryService.uses_username_password_auth(delivery)
            or delivery.get("delivery_type") == "openvpn_credentials"
        ):
            await bot.send_message(
                int(chat_id),
                OpenVpnCredentialDeliveryService.format_telegram_message(
                    delivery,
                    view_only=view_only or not delivery.get("includes_password"),
                ),
                reply_markup=reply_markup if not delivery.get("content") else None,
                parse_mode="HTML",
            )

        if delivery.get("delivery_type") in {"file", "openvpn_package"} and delivery.get("content"):
            document = BufferedInputFile(
                delivery["content"].encode("utf-8"),
                filename=delivery.get("filename") or "config.ovpn",
            )
            config_id = delivery.get("config_id") or (
                str(delivery.get("filename", "")).removesuffix(".ovpn") or "—"
            )
            if OpenVpnCredentialDeliveryService.uses_username_password_auth(delivery):
                caption = (
                    "📂 <b>فایل کانفیگ OpenVPN</b>\n\n"
                    f"🆔 کد کانفیگ: <code>{config_id}</code>"
                )
            else:
                caption = (
                    "🎉 <b>سرویس شما آماده است!</b>\n\n"
                    f"🆔 کد کانفیگ: <code>{config_id}</code>\n"
                    "📂 فایل کانفیگ OpenVPN\n"
                    "⚡ همین الان وارد شو و لذت ببر!"
                )
            await bot.send_document(
                int(chat_id),
                document,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        elif delivery.get("delivery_type") == "link":
            await bot.send_message(
                int(chat_id),
                "🎉 <b>لینک سرویس V2Ray شما:</b>\n\n"
                f"🔗 <code>{delivery['content']}</code>\n\n"
                "⚡ لینک را در برنامه V2Ray وارد کن.",
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        elif delivery.get("delivery_type") == "openvpn_credentials":
            return True
        else:
            return False
        return True
    except Exception:
        LOGGER.exception("Failed to deliver configuration to chat_id=%s", chat_id)
        return False


async def send_delivery_to_chat(
    bot,
    chat_id: str | int,
    delivery: dict,
    *,
    reply_markup=None,
) -> bool:
    return await send_openvpn_delivery_to_chat(
        bot,
        chat_id,
        delivery,
        reply_markup=reply_markup,
    )


async def resolve_purchase_delivery(
    api: UserManagerApiClient,
    telegram_id: str,
    result: dict | None,
) -> dict | None:
    if not result:
        return None

    delivery = result.get("delivery")
    if delivery:
        return delivery

    purchase = result.get("purchase")
    if isinstance(purchase, dict) and purchase.get("delivery"):
        return purchase["delivery"]

    subscription = None
    if isinstance(purchase, dict):
        subscription = purchase.get("subscription")
    subscription = subscription or result.get("subscription")
    subscription_id = (subscription or {}).get("id")
    if not subscription_id:
        return None

    try:
        return await api.get_subscription_delivery(telegram_id, subscription_id)
    except httpx.HTTPStatusError:
        LOGGER.warning(
            "Could not resolve delivery for subscription %s (telegram_id=%s)",
            subscription_id,
            telegram_id,
        )
        return None


ADMIN_FORBIDDEN_MESSAGE = (
    "⛔ دسترسی ادمین ندارید.\n"
    "شناسه تلگرام شما باید در ADMIN_CHAT_IDS (یا TELEGRAM_ADMIN_IDS) تنظیم شده باشد."
)


def is_admin(user_id: int | str, bot_config: TelegramBotConfig) -> bool:
    return str(user_id) in bot_config.admin_chat_ids


async def guard_admin_callback(callback: CallbackQuery, bot_config: TelegramBotConfig) -> bool:
    if is_admin(callback.from_user.id, bot_config):
        return True
    await answer_callback(callback, "⛔ دسترسی ادمین لازم است", show_alert=True)
    return False


async def require_callback_message(callback: CallbackQuery) -> Message | None:
    if callback.message:
        return callback.message
    await answer_callback(
        callback,
        "پیام اصلی در دسترس نیست. از /start دوباره شروع کن.",
        show_alert=True,
    )
    return None


async def handle_admin_api_error(event: CallbackQuery | Message, exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code == 403:
            if isinstance(event, CallbackQuery):
                await answer_callback(event, ADMIN_FORBIDDEN_MESSAGE, show_alert=True)
            else:
                await event.answer(ADMIN_FORBIDDEN_MESSAGE)
            return True
        if exc.response.status_code == 400:
            detail = exc.response.text
            try:
                payload = exc.response.json()
                detail = payload.get("detail", detail)
            except Exception:
                pass
            message = f"⚠️ خطا: {detail}"
            if isinstance(event, CallbackQuery):
                await answer_callback(event, message, show_alert=True)
            else:
                await event.answer(message)
            return True
    return False
