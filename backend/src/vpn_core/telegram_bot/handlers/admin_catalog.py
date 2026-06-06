from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.config import TelegramBotConfig
from vpn_core.telegram_bot.handlers.common import guard_admin_callback, handle_admin_api_error, is_admin
from vpn_core.telegram_bot.keyboards.main import (
    admin_menu_keyboard,
    admin_payment_method_detail_keyboard,
    admin_payment_methods_keyboard,
    admin_plan_service_types_keyboard,
    admin_plans_keyboard,
    admin_report_keyboard,
)
from vpn_core.telegram_bot.messages import (
    format_financial_report,
    format_payment_method_display,
    format_toman,
)
from vpn_core.telegram_bot.states import AdminFlow

router = Router()


def _admin_id(callback: CallbackQuery) -> str:
    return str(callback.from_user.id)


@router.callback_query(F.data == "admin:plan:add")
async def admin_plan_add_start(
    callback: CallbackQuery,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    try:
        services = await api.list_service_types_admin(_admin_id(callback))
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        raise
    if not services:
        await message.edit_text(
            "😔 نوع سرویسی تعریف نشده.\nاول از «انواع سرویس» یک سرویس فعال کن.",
            reply_markup=admin_plans_keyboard(),
        )
    else:
        await message.edit_text(
            "📋 <b>افزودن پلن جدید</b>\n\n👇 نوع سرویس را انتخاب کن:",
            reply_markup=admin_plan_service_types_keyboard(services),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:plan:add:type:"))
async def admin_plan_add_type(
    callback: CallbackQuery,
    state: FSMContext,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    service_type = callback.data.rsplit(":", 1)[1]
    await state.set_state(AdminFlow.create_plan_name)
    await state.update_data(service_type=service_type)
    await message.edit_text(
        "✏️ <b>نام پلن</b> را بنویس:\n<i>مثال: پلن یک ماهه ۵۰ گیگ</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminFlow.create_plan_name)
async def admin_plan_receive_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("⚠️ نام پلن نمی‌تواند خالی باشد.")
        return
    await state.update_data(name=name)
    await state.set_state(AdminFlow.create_plan_duration)
    await message.answer(
        "📅 <b>مدت (روز)</b> را بنویس:\n<i>مثال: 30</i>",
        parse_mode="HTML",
    )


@router.message(AdminFlow.create_plan_duration)
async def admin_plan_receive_duration(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit() or int(text) <= 0:
        await message.answer("⚠️ لطفاً تعداد روز را به صورت عدد مثبت وارد کن.")
        return
    await state.update_data(duration_days=int(text))
    await state.set_state(AdminFlow.create_plan_traffic_gb)
    await message.answer(
        "📊 <b>حجم (گیگابایت)</b> را بنویس:\n<i>مثال: 50</i>",
        parse_mode="HTML",
    )


@router.message(AdminFlow.create_plan_traffic_gb)
async def admin_plan_receive_traffic(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text.isdigit() or int(text) <= 0:
        await message.answer("⚠️ لطفاً حجم را به صورت عدد مثبت (گیگ) وارد کن.")
        return
    await state.update_data(traffic_gb=int(text))
    await state.set_state(AdminFlow.create_plan_price)
    await message.answer(
        "💰 <b>قیمت (تومان)</b> را بنویس:\n<i>مثال: 150000</i>",
        parse_mode="HTML",
    )


@router.message(AdminFlow.create_plan_price)
async def admin_plan_receive_price(
    message: Message,
    state: FSMContext,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    if not is_admin_message(message, bot_config):
        await message.answer("⛔ دسترسی ادمین لازم است.")
        return
    text = (message.text or "").strip()
    if not text.isdigit() or int(text) < 0:
        await message.answer("⚠️ لطفاً قیمت را به صورت عدد غیرمنفی وارد کن.")
        return
    data = await state.get_data()
    await state.clear()
    payload = {
        "name": data["name"],
        "service_type": data["service_type"],
        "duration_days": data["duration_days"],
        "traffic_limit_bytes": data["traffic_gb"] * (1024**3),
        "price_toman": int(text),
        "is_active": True,
    }
    try:
        plan = await api.create_plan_admin(str(message.from_user.id), payload)
    except Exception as exc:
        if await handle_admin_api_error(message, exc):
            return
        raise
    gb = plan["traffic_limit_bytes"] / (1024**3)
    await message.answer(
        "✅ <b>پلن ایجاد شد!</b>\n\n"
        f"#{plan['id']} [{plan['service_type']}] {plan['name']}\n"
        f"{gb:.0f}GB / {plan['duration_days']}روز — {format_toman(plan['price_toman'])}",
        reply_markup=admin_plans_keyboard(),
        parse_mode="HTML",
    )


def is_admin_message(message: Message, bot_config: TelegramBotConfig) -> bool:
    return is_admin(message.from_user.id, bot_config)


@router.callback_query(F.data == "admin:payment-methods")
async def admin_payment_methods_list(
    callback: CallbackQuery,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    try:
        methods = await api.list_payment_methods_admin(_admin_id(callback))
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        raise
    if not methods:
        await message.edit_text(
            "💳 روش پرداختی تعریف نشده.\n➕ یک روش جدید اضافه کن:",
            reply_markup=admin_payment_methods_keyboard([]),
        )
    else:
        lines = []
        for method in methods:
            state = "🟢" if method.get("is_active", True) else "🔴"
            lines.append(f"{state} <b>{method['name']}</b> (#{method['id']})")
        await message.edit_text(
            "💳 <b>روش‌های پرداخت</b>\n\n" + "\n".join(lines) + "\n\n👇 برای مدیریت انتخاب کن:",
            reply_markup=admin_payment_methods_keyboard(methods),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "admin:pm:add")
async def admin_pm_add_start(
    callback: CallbackQuery,
    state: FSMContext,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    await state.set_state(AdminFlow.create_pm_name)
    await message.edit_text(
        "✏️ <b>نام روش پرداخت</b> را بنویس:\n<i>مثال: کارت به کارت</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminFlow.create_pm_name)
async def admin_pm_receive_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("⚠️ نام نمی‌تواند خالی باشد.")
        return
    await state.update_data(name=name)
    await state.set_state(AdminFlow.create_pm_instructions)
    await message.answer(
        "📝 <b>دستورالعمل پرداخت</b> را بنویس:\n<i>مثال: به نام فلانی واریز کنید</i>",
        parse_mode="HTML",
    )


@router.message(AdminFlow.create_pm_instructions)
async def admin_pm_receive_instructions(message: Message, state: FSMContext) -> None:
    await state.update_data(instructions=(message.text or "").strip())
    await state.set_state(AdminFlow.create_pm_card_numbers)
    await message.answer(
        "💳 <b>شماره کارت‌ها</b> را هر کدام در یک خط بنویس:\n"
        "<i>برای رد کردن، خط خالی یا - بفرست</i>",
        parse_mode="HTML",
    )


@router.message(AdminFlow.create_pm_card_numbers)
async def admin_pm_receive_cards(
    message: Message,
    state: FSMContext,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    if not is_admin_message(message, bot_config):
        await message.answer("⛔ دسترسی ادمین لازم است.")
        return
    raw = (message.text or "").strip()
    card_numbers: list[str] = []
    if raw and raw != "-":
        card_numbers = [line.strip() for line in raw.splitlines() if line.strip()]
    data = await state.get_data()
    await state.clear()
    payload = {
        "name": data["name"],
        "instructions": data.get("instructions", ""),
        "card_numbers": card_numbers,
        "is_active": True,
    }
    try:
        method = await api.create_payment_method_admin(str(message.from_user.id), payload)
    except Exception as exc:
        if await handle_admin_api_error(message, exc):
            return
        raise
    await message.answer(
        "✅ <b>روش پرداخت ایجاد شد!</b>\n\n" + format_payment_method_display(method),
        reply_markup=admin_payment_methods_keyboard([method]),
        parse_mode="HTML",
    )


@router.callback_query(F.data.regexp(r"^admin:pm:\d+$"))
async def admin_pm_detail(
    callback: CallbackQuery,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    method_id = int(callback.data.rsplit(":", 1)[1])
    try:
        methods = await api.list_payment_methods_admin(_admin_id(callback))
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        raise
    method = next((item for item in methods if item["id"] == method_id), None)
    if not method:
        await callback.answer("❌ روش پرداخت یافت نشد", show_alert=True)
        return
    state = "فعال" if method.get("is_active", True) else "غیرفعال"
    await message.edit_text(
        f"💳 <b>{method['name']}</b> (#{method_id}) — {state}\n\n"
        f"{format_payment_method_display(method)}",
        reply_markup=admin_payment_method_detail_keyboard(
            method_id,
            is_active=method.get("is_active", True),
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:pm:toggle:(enable|disable):\d+$"))
async def admin_pm_toggle(
    callback: CallbackQuery,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    _, _, _, action, method_id_str = callback.data.split(":", 4)
    method_id = int(method_id_str)
    is_active = action == "enable"
    try:
        method = await api.update_payment_method_admin(
            _admin_id(callback),
            method_id,
            {"is_active": is_active},
        )
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        raise
    state = "فعال" if method.get("is_active", True) else "غیرفعال"
    await message.edit_text(
        f"💳 <b>{method['name']}</b> (#{method_id}) — {state}\n\n"
        f"{format_payment_method_display(method)}",
        reply_markup=admin_payment_method_detail_keyboard(
            method_id,
            is_active=method.get("is_active", True),
        ),
        parse_mode="HTML",
    )
    await callback.answer("✅ به‌روز شد")


@router.callback_query(F.data.regexp(r"^admin:pm:delete:\d+$"))
async def admin_pm_delete(
    callback: CallbackQuery,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    method_id = int(callback.data.rsplit(":", 1)[1])
    try:
        await api.delete_payment_method_admin(_admin_id(callback), method_id)
        methods = await api.list_payment_methods_admin(_admin_id(callback))
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        raise
    if not methods:
        await message.edit_text(
            "🗑 روش پرداخت حذف شد.\n💳 روش دیگری تعریف نشده.",
            reply_markup=admin_payment_methods_keyboard([]),
        )
    else:
        lines = [f"{'🟢' if m.get('is_active', True) else '🔴'} <b>{m['name']}</b> (#{m['id']})" for m in methods]
        await message.edit_text(
            "🗑 <b>حذف شد.</b>\n\n💳 <b>روش‌های پرداخت</b>\n\n" + "\n".join(lines),
            reply_markup=admin_payment_methods_keyboard(methods),
            parse_mode="HTML",
        )
    await callback.answer("🗑 حذف شد")


@router.callback_query(F.data == "admin:report")
async def admin_report_menu(callback: CallbackQuery, bot_config: TelegramBotConfig) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    await message.edit_text(
        "📊 <b>گزارش مالی</b>\n\n👇 بازه زمانی را انتخاب کن:",
        reply_markup=admin_report_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:report:(daily|weekly|monthly)$"))
async def admin_report_show(
    callback: CallbackQuery,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    period = callback.data.rsplit(":", 1)[1]
    try:
        report = await api.get_financial_report_admin(_admin_id(callback), period)
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        raise
    await message.edit_text(
        format_financial_report(report),
        reply_markup=admin_report_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()
