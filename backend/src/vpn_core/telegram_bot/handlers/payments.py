from aiogram import F, Router
from aiogram.types import Message

from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.config import TelegramBotConfig
from vpn_core.telegram_bot.handlers.common import ensure_user, telegram_id
from vpn_core.telegram_bot.keyboards.main import admin_payment_keyboard, buy_now_keyboard
from vpn_core.telegram_bot.messages import PURPOSE_FA, format_toman

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
        await message.answer(
            "⚠️ درخواست پرداخت فعالی پیدا نشد.\n\n"
            "🛒 اول از منو «خرید سرویس» یا «شارژ کیف پول» را انتخاب کن.",
            reply_markup=buy_now_keyboard(),
            parse_mode="HTML",
        )
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
    await message.answer(
        "✅ <b>رسید دریافت شد!</b>\n\n"
        "⏳ در انتظار تأیید ادمین...\n"
        "🎉 بعد از تأیید، سرویس یا موجودی فوراً فعال می‌شود!\n\n"
        "💡 می‌توانید در همین حال سرویس‌های دیگر را هم ببینید 👇",
        reply_markup=buy_now_keyboard(),
        parse_mode="HTML",
    )
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
    purpose = PURPOSE_FA.get(payment_request["purpose"], payment_request["purpose"])
    text = (
        "🔔 <b>بررسی پرداخت</b>\n\n"
        f"🧾 شماره: #{payment_request['id']}\n"
        f"📌 نوع: {purpose}\n"
        f"💰 مبلغ: {format_toman(payment_request['amount_toman'])}\n\n"
        f"🆔 کاربر: {user_obj['id']}\n"
        f"📱 تلگرام: {user_obj['telegram_id']}\n"
        f"👤 @{user_obj.get('username') or '—'}\n"
        f"💳 موجودی: {format_toman(wallet['balance_toman'])}"
    )
    markup = admin_payment_keyboard(payment_request["id"])
    for admin_id in bot_config.admin_chat_ids:
        try:
            await message.bot.send_photo(admin_id, photo, caption=text, reply_markup=markup, parse_mode="HTML")
        except Exception:
            await message.bot.send_message(admin_id, text, reply_markup=markup, parse_mode="HTML")
