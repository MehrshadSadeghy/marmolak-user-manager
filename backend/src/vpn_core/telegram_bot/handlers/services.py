from aiogram import F, Router
from aiogram.types import CallbackQuery

from vpn_core.billing_domain.domain.payment_request import PaymentPurpose
from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.handlers.common import send_delivery
from vpn_core.telegram_bot.keyboards.main import payment_methods_keyboard, plans_keyboard, renew_services_keyboard

router = Router()


@router.callback_query(F.data == "menu:services")
async def menu_services(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    services = await api.list_user_services(str(callback.from_user.id))
    if not services:
        await message.edit_text("You do not have any services yet.")
    else:
        lines = []
        for item in services:
            lines.append(
                f"#{item['subscription_id']} {item['service_type']} — {item['status_label']}\n"
                f"Plan: {item['plan_name'] or '-'}\n"
                f"Remaining: {item['remaining_days']} days, {item['remaining_data_label']}"
            )
        await message.edit_text("Your services:\n\n" + "\n\n".join(lines))
    await callback.answer()


@router.callback_query(F.data == "menu:renew")
async def menu_renew(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    services = await api.list_user_services(str(callback.from_user.id))
    if not services:
        await message.edit_text("You do not have any services to renew.")
    else:
        await message.edit_text("Select a service to renew:", reply_markup=renew_services_keyboard(services))
    await callback.answer()


@router.callback_query(F.data.startswith("renew:sub:"))
async def renew_subscription(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    subscription_id = int(callback.data.rsplit(":", 1)[1])
    tg_id = str(callback.from_user.id)
    services = await api.list_user_services(tg_id)
    selected = next(s for s in services if s["subscription_id"] == subscription_id)
    if selected["is_active"]:
        await message.edit_text(
            f"Service #{subscription_id} is active.\n"
            f"Remaining time: {selected['remaining_days']} days\n"
            f"Remaining data: {selected['remaining_data_label']}"
        )
        await callback.answer()
        return
    plans = await api.list_plans(selected["service_type"])
    if not plans:
        await message.edit_text("No plans are available for renewal.")
    else:
        await message.edit_text(
            "Select a renewal plan:",
            reply_markup=plans_keyboard(plans, prefix=f"renew:{subscription_id}"),
        )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^renew:\d+:plan:\d+$"))
async def renew_plan(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    _, subscription_id, _, plan_id = callback.data.split(":")
    tg_id = str(callback.from_user.id)
    preview = await api.preview_purchase(tg_id, int(plan_id))
    if preview["sufficient_balance"]:
        result = await api.renew(tg_id, int(subscription_id), int(plan_id))
        await message.edit_text(
            "Renewal completed from wallet.\n"
            f"New balance: {result['wallet_balance_toman']} Toman"
        )
        await send_delivery(message, result.get("delivery"))
    else:
        methods = await api.list_payment_methods()
        if not methods:
            await message.edit_text("Insufficient wallet balance and no payment methods are configured.")
        else:
            await message.edit_text(
                "Insufficient wallet balance for renewal.\nSelect a payment method:",
                reply_markup=payment_methods_keyboard(
                    methods,
                    prefix=f"renewpay:{subscription_id}:{plan_id}",
                ),
            )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^renewpay:\d+:\d+:pay:\d+$"))
async def renew_with_payment(callback: CallbackQuery, api: UserManagerApiClient) -> None:
    message = callback.message
    if not message:
        await callback.answer()
        return
    _, subscription_id, plan_id, _, method_id = callback.data.split(":")
    tg_id = str(callback.from_user.id)
    payment = await api.initiate_payment(
        {
            "telegram_id": tg_id,
            "purpose": PaymentPurpose.renewal.value,
            "amount_toman": 0,
            "plan_id": int(plan_id),
            "subscription_id": int(subscription_id),
            "payment_method_id": int(method_id),
        }
    )
    methods = await api.list_payment_methods()
    method = next(m for m in methods if m["id"] == int(method_id))
    await message.edit_text(
        "Renewal payment initiated.\n"
        f"Amount: {payment['payment_request']['amount_toman']} Toman\n\n"
        f"{method['name']}\n{method['instructions']}\n\n"
        "Please upload your payment receipt as a photo in this chat."
    )
    await callback.answer()
