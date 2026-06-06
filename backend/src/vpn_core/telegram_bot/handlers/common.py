from aiogram.types import BufferedInputFile, Message

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
    if not delivery:
        return
    if delivery["delivery_type"] == "file":
        document = BufferedInputFile(
            delivery["content"].encode("utf-8"),
            filename=delivery.get("filename") or "config.ovpn",
        )
        await message.answer_document(
            document,
            caption=(
                "🎉 <b>سرویس شما آماده است!</b>\n\n"
                "📂 فایل کانفیگ OpenVPN\n"
                "⚡ همین الان وارد شو و لذت ببر!\n\n"
                "💡 سرویس دیگری هم می‌خواهی؟ 👇"
            ),
            reply_markup=buy_now_keyboard(),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            "🎉 <b>لینک سرویس V2Ray شما:</b>\n\n"
            f"🔗 <code>{delivery['content']}</code>\n\n"
            "⚡ لینک را در برنامه V2Ray وارد کن.\n"
            "💡 سرویس دیگری هم می‌خواهی؟ از منو «خرید سرویس» را بزن!",
            reply_markup=buy_now_keyboard(),
            parse_mode="HTML",
        )
