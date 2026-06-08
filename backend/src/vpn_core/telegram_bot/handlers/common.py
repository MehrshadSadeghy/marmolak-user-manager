import httpx
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from vpn_core.telegram_bot.config import TelegramBotConfig

from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.keyboards.main import buy_now_keyboard


def telegram_id(message: Message) -> str:
    return str(message.from_user.id)


def chat_id(message: Message) -> str:
    return str(message.chat.id)


def username(message: Message) -> str | None:
    return message.from_user.username


async def ensure_user(api: UserManagerApiClient, message: Message) -> dict:
    return await api.register_user(telegram_id(message), chat_id(message), username(message))


async def send_delivery(message: Message, delivery: dict) -> None:
    await send_delivery_to_chat(
        message.bot,
        message.chat.id,
        delivery,
        reply_markup=buy_now_keyboard(),
    )


async def send_delivery_to_chat(
    bot,
    chat_id: str | int,
    delivery: dict,
    *,
    reply_markup=None,
) -> None:
    if not delivery:
        return
    if delivery["delivery_type"] == "file":
        document = BufferedInputFile(
            delivery["content"].encode("utf-8"),
            filename=delivery.get("filename") or "config.ovpn",
        )
        config_id = delivery.get("filename", "").removesuffix(".ovpn") or "—"
        await bot.send_document(
            chat_id,
            document,
            caption=(
                "🎉 <b>سرویس شما آماده است!</b>\n\n"
                f"🆔 کد کانفیگ: <code>{config_id}</code>\n"
                "📂 فایل کانفیگ OpenVPN\n"
                "⚡ همین الان وارد شو و لذت ببر!"
            ),
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
    else:
        await bot.send_message(
            chat_id,
            "🎉 <b>لینک سرویس V2Ray شما:</b>\n\n"
            f"🔗 <code>{delivery['content']}</code>\n\n"
            "⚡ لینک را در برنامه V2Ray وارد کن.",
            reply_markup=reply_markup,
            parse_mode="HTML",
        )


ADMIN_FORBIDDEN_MESSAGE = (
    "⛔ دسترسی ادمین ندارید.\n"
    "شناسه تلگرام شما باید در ADMIN_CHAT_IDS (یا TELEGRAM_ADMIN_IDS) تنظیم شده باشد."
)


def is_admin(user_id: int | str, bot_config: TelegramBotConfig) -> bool:
    return str(user_id) in bot_config.admin_chat_ids


async def guard_admin_callback(callback: CallbackQuery, bot_config: TelegramBotConfig) -> bool:
    if is_admin(callback.from_user.id, bot_config):
        return True
    await callback.answer("⛔ دسترسی ادمین لازم است", show_alert=True)
    return False


async def handle_admin_api_error(event: CallbackQuery | Message, exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code == 403:
            if isinstance(event, CallbackQuery):
                await event.answer(ADMIN_FORBIDDEN_MESSAGE, show_alert=True)
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
                await event.answer(message, show_alert=True)
            else:
                await event.answer(message)
            return True
    return False
