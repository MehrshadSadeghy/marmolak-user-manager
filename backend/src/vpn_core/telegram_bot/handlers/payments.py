from aiogram import F, Router
from aiogram.types import Message

from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.config import TelegramBotConfig
from vpn_core.telegram_bot.handlers.common import ensure_user, send_delivery, telegram_id
from vpn_core.telegram_bot.keyboards.main import admin_payment_keyboard

router = Router()


@router.message(F.photo)
async def receive_receipt_photo(
    message: Message,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    user = await ensure_user(api, message)
    tg_id = telegram_id(message)
    wallet = await api.get_wallet(tg_id)

    try:
        active = await api.get_active_payment(tg_id)
    except Exception:
        await message.answer("No active payment request found. Start a purchase or top-up first.")
        return

    payment_request_id = active["payment_request"]["id"]
    largest_photo = message.photo[-1]
    submitted = await api.submit_receipt(
        payment_request_id,
        {
            "telegram_id": tg_id,
            "receipt_file_id": largest_photo.file_id,
            "receipt_message_id": message.message_id,
        },
    )
    await message.answer("Waiting for approval. An admin will review your payment soon.")
    await _notify_admins(
        message,
        bot_config,
        user,
        wallet,
        submitted["payment_request"],
        photo=largest_photo.file_id,
    )


async def _notify_admins(
    message: Message,
    bot_config: TelegramBotConfig,
    user: dict,
    wallet: dict,
    payment_request: dict,
    *,
    photo: str,
) -> None:
    user_obj = user["user"]
    text = (
        "Payment review required\n"
        f"Payment ID: {payment_request['id']}\n"
        f"Purpose: {payment_request['purpose']}\n"
        f"Amount: {payment_request['amount_toman']} Toman\n"
        f"User ID: {user_obj['id']}\n"
        f"Telegram ID: {user_obj['telegram_id']}\n"
        f"Username: @{user_obj.get('username') or '-'}\n"
        f"Wallet balance: {wallet['balance_toman']} Toman"
    )
    markup = admin_payment_keyboard(payment_request["id"])
    for admin_id in bot_config.admin_chat_ids:
        try:
            await message.bot.send_photo(admin_id, photo, caption=text, reply_markup=markup)
        except Exception:
            await message.bot.send_message(admin_id, text, reply_markup=markup)
