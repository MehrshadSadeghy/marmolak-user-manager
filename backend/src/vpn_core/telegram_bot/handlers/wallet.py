from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from vpn_core.billing_domain.domain.payment_request import PaymentPurpose
from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.keyboards.main import back_to_menu_keyboard, payment_methods_keyboard
from vpn_core.telegram_bot.messages import format_toman
from vpn_core.telegram_bot.states import UserFlow

router = Router()


@router.callback_query(F.data == "menu:topup")
async def menu_topup(callback: CallbackQuery, state: FSMContext) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    await state.set_state(UserFlow.waiting_topup_amount)
    await message.edit_text(
        "💳 <b>شارژ کیف پول</b>\n\n"
        "💰 با شارژ کیف پول، خرید بعدی <b>فوری و بدون دردسر</b> انجام می‌شود!\n\n"
        "✏️ مبلغ مورد نظر را به <b>تومان</b> بنویس:\n"
        "<i>مثال: 50000</i>",
        parse_mode="HTML",
    )
    await callback.answer("💳 شارژ کیف پول")


@router.message(UserFlow.waiting_topup_amount)
async def receive_topup_amount(message: Message, state: FSMContext, api: UserManagerApiClient) -> None:
    text = (message.text or "").strip()
    if not text.isdigit() or int(text) <= 0:
        await message.answer("⚠️ لطفاً یک عدد مثبت معتبر وارد کن.\n<i>مثال: 100000</i>", parse_mode="HTML")
        return
    amount = int(text)
    await state.clear()
    methods = await api.list_payment_methods()
    if not methods:
        await message.answer(
            "😔 روش پرداختی تنظیم نشده.\n📞 با پشتیبانی تماس بگیر.",
            reply_markup=back_to_menu_keyboard(),
        )
        return
    await message.answer(
        f"💰 مبلغ شارژ: <b>{format_toman(amount)}</b>\n\n"
        "👇 روش پرداخت را انتخاب کن:",
        reply_markup=payment_methods_keyboard(methods, prefix=f"topup:{amount}"),
        parse_mode="HTML",
    )


@router.callback_query(F.data.regexp(r"^topup:\d+:pay:\d+$"))
async def topup_payment(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    _, amount, _, method_id = callback.data.split(":")
    tg_id = str(callback.from_user.id)
    payment = await api.initiate_payment(
        {
            "telegram_id": tg_id,
            "purpose": PaymentPurpose.topup.value,
            "amount_toman": int(amount),
            "payment_method_id": int(method_id),
        }
    )
    methods = await api.list_payment_methods()
    method = next(m for m in methods if m["id"] == int(method_id))
    support = await api.get_support()
    instructions = support.get("payment_instructions") or ""
    await message.edit_text(
        "💸 <b>درخواست شارژ کیف پول ثبت شد</b>\n\n"
        f"💰 مبلغ: <b>{format_toman(payment['payment_request']['amount_toman'])}</b>\n\n"
        f"🏦 <b>{method['name']}</b>\n"
        f"{method['instructions']}\n\n"
        f"{instructions}\n\n"
        "📸 بعد از پرداخت، <b>عکس رسید</b> را همینجا بفرست.\n"
        "⏳ بعد از تأیید، موجودی به کیف پولت اضافه می‌شود!",
        parse_mode="HTML",
    )
    await callback.answer("📸 منتظر رسید")
