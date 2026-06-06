from aiogram import F, Router
from aiogram.types import CallbackQuery

from vpn_core.billing_domain.domain.payment_request import PaymentPurpose
from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.handlers.common import send_delivery
from vpn_core.telegram_bot.keyboards.main import payment_methods_keyboard, plans_keyboard, services_keyboard

router = Router()


@router.callback_query(F.data == "menu:buy")
async def menu_buy(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    services = await api.list_services()
    if not services:
        await message.edit_text("No services are available right now.")
    else:
        await message.edit_text("Select a service:", reply_markup=services_keyboard(services))
    await callback.answer()


@router.callback_query(F.data.startswith("service:"))
async def select_service(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    service_type = callback.data.split(":", 1)[1]
    plans = await api.list_plans(service_type)
    if not plans:
        await message.edit_text("No plans are available for this service.")
    else:
        await message.edit_text("Select a plan:", reply_markup=plans_keyboard(plans, prefix="buy"))
    await callback.answer()


@router.callback_query(F.data.startswith("buy:plan:"))
async def select_plan(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    plan_id = int(callback.data.rsplit(":", 1)[1])
    tg_id = str(callback.from_user.id)
    preview = await api.preview_purchase(tg_id, plan_id)
    if preview["sufficient_balance"]:
        result = await api.purchase(tg_id, plan_id)
        await message.edit_text(
            "Purchase completed from wallet.\n"
            f"New balance: {result['wallet_balance_toman']} Toman"
        )
        await send_delivery(message, result.get("delivery"))
    else:
        methods = await api.list_payment_methods()
        if not methods:
            await message.edit_text("Insufficient wallet balance and no payment methods are configured.")
        else:
            await message.edit_text(
                "Insufficient wallet balance.\n"
                f"Required: {preview['price_toman']} Toman\n"
                f"Your balance: {preview['wallet_balance_toman']} Toman\n\n"
                "Select a payment method:",
                reply_markup=payment_methods_keyboard(methods, prefix=f"buy:{plan_id}"),
            )
    await callback.answer()


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
    await message.edit_text(
        "Payment initiated.\n"
        f"Amount: {payment['payment_request']['amount_toman']} Toman\n\n"
        f"{method['name']}\n{method['instructions']}\n\n"
        f"{instructions}\n\n"
        "Please upload your payment receipt as a photo in this chat."
    )
    await callback.answer()
