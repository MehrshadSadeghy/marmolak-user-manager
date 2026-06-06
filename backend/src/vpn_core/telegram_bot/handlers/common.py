from aiogram.types import BufferedInputFile, Message

from vpn_core.telegram_bot.client.api_client import UserManagerApiClient


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
        await message.answer_document(document, caption="Your VPN configuration")
    else:
        await message.answer("Your service link:\n" + delivery["content"])
