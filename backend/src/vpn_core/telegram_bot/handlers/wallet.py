from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from vpn_core.billing_domain.domain.payment_request import PaymentPurpose
from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.keyboards.main import back_to_menu_keyboard, payment_methods_keyboard
from vpn_core.telegram_bot.states import UserFlow

router = Router()


@router.callback_query(F.data == "menu:topup")
async def menu_topup(callback: CallbackQuery, state: FSMContext) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    await state.set_state(UserFlow.waiting_topup_amount)
    await message.edit_text("Enter the amount you want to top up (in Toman):")
    await callback.answer()


@router.message(UserFlow.waiting_topup_amount)
async def receive_topup_amount(message: Message, state: FSMContext, api: UserManagerApiClient) -> None:
    text = (message.text or "").strip()
    if not text.isdigit() or int(text) <= 0:
        await message.answer("Please send a valid positive number.")
        return
    amount = int(text)
    await state.clear()
    methods = await api.list_payment_methods()
    if not methods:
        await message.answer("No payment methods are configured.", reply_markup=back_to_menu_keyboard())
        return
    await message.answer(
        f"Top-up amount: {amount} Toman\nSelect a payment method:",
        reply_markup=payment_methods_keyboard(methods, prefix=f"topup:{amount}"),
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
        "Top-up payment initiated.\n"
        f"Amount: {payment['payment_request']['amount_toman']} Toman\n\n"
        f"{method['name']}\n{method['instructions']}\n\n"
        f"{instructions}\n\n"
        "Please upload your payment receipt as a photo in this chat."
    )
    await callback.answer()
