from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.config import TelegramBotConfig
from vpn_core.telegram_bot.handlers.common import guard_admin_callback, handle_admin_api_error
from vpn_core.telegram_bot.keyboards.main import (
    admin_collaborator_discount_keyboard,
    admin_collaborator_service_keyboard,
    admin_user_config_detail_keyboard,
    admin_user_configs_keyboard,
    admin_user_detail_keyboard,
    admin_users_list_keyboard,
)
from vpn_core.telegram_bot.states import AdminFlow

router = Router()


def _format_bytes(value: int) -> str:
    gb = value / (1024**3)
    if gb >= 1:
        return f"{gb:.2f} GB"
    mb = value / (1024**2)
    return f"{mb:.0f} MB"


def _format_date(value: str | datetime | None) -> str:
    if not value:
        return "—"
    if isinstance(value, str):
        return value[:10]
    return value.strftime("%Y-%m-%d")


def _users_list_text(data: dict, search_query: str | None = None) -> str:
    header = "👥 <b>مدیریت کاربران</b>\n\n"
    if search_query:
        header += f"🔍 جستجو: <code>{search_query}</code>\n"
    header += (
        f"📄 صفحه {data['page']} از {data['total_pages']} "
        f"({data['total_items']} کاربر)\n\n"
        "👇 برای مشاهده جزئیات، کاربر را انتخاب کن:"
    )
    return header


def _user_detail_text(user: dict) -> str:
    status = "🚫 مسدود" if user.get("is_blocked") else "✅ فعال"
    collab = "🤝 همکار" if user.get("is_collaborator") else "👤 کاربر عادی"
    rules = user.get("discount_rules") or []
    rules_text = "\n".join(
        f"• {rule['service_type']}: {rule['discount_percent']}%" for rule in rules
    ) or "—"
    return (
        "👤 <b>پروفایل کاربر</b>\n\n"
        f"🆔 شناسه داخلی: <code>{user['id']}</code>\n"
        f"📱 Telegram ID: <code>{user['telegram_id']}</code>\n"
        f"👤 نام کاربری: @{user.get('username') or '—'}\n"
        f"📅 تاریخ ثبت‌نام: {_format_date(user.get('created_at'))}\n"
        f"🛒 تعداد خریدها: <b>{user.get('total_purchased_plans', 0)}</b>\n"
        f"📁 کانفیگ‌های فعال: <b>{user.get('total_active_configs', 0)}</b>\n"
        f"📊 حجم مصرفی: <b>{_format_bytes(user.get('total_traffic_used_bytes', 0))}</b>\n"
        f"📌 وضعیت: {status}\n"
        f"🏷️ نقش: {collab}\n"
        f"💸 تخفیف‌های فعال:\n{rules_text}"
    )


def _config_detail_text(config: dict) -> str:
    return (
        "🔐 <b>جزئیات کانفیگ</b>\n\n"
        f"🆔 Config ID: <code>{config['config_id']}</code>\n"
        f"📅 ایجاد: {_format_date(config.get('created_at'))}\n"
        f"⏳ انقضا: {_format_date(config.get('expire_at'))}\n"
        f"📊 سقف حجم: {_format_bytes(config.get('traffic_limit_bytes', 0))}\n"
        f"📈 مصرف: {_format_bytes(config.get('traffic_used_bytes', 0))}\n"
        f"📉 باقی‌مانده: {_format_bytes(config.get('remaining_traffic_bytes', 0))}\n"
        f"📌 وضعیت: <b>{config.get('status')}</b>"
    )


async def _load_users_page(
    api: UserManagerApiClient,
    admin_id: str,
    *,
    page: int = 1,
    search_query: str | None = None,
) -> dict:
    return await api.list_admin_users(
        admin_id,
        page=page,
        page_size=20,
        query=search_query,
    )


@router.callback_query(F.data == "admin:users")
async def admin_users_home(
    callback: CallbackQuery,
    state: FSMContext,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    await state.clear()
    admin_id = str(callback.from_user.id)
    try:
        data = await _load_users_page(api, admin_id, page=1)
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        raise
    await message.edit_text(
        _users_list_text(data),
        reply_markup=admin_users_list_keyboard(
            data["users"],
            page=data["page"],
            total_pages=data["total_pages"],
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:users:page:"))
async def admin_users_page(
    callback: CallbackQuery,
    state: FSMContext,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    page = int(callback.data.rsplit(":", 1)[1])
    state_data = await state.get_data()
    search_query = state_data.get("user_search_query")
    admin_id = str(callback.from_user.id)
    try:
        data = await _load_users_page(api, admin_id, page=page, search_query=search_query)
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        raise
    await message.edit_text(
        _users_list_text(data, search_query=search_query),
        reply_markup=admin_users_list_keyboard(
            data["users"],
            page=data["page"],
            total_pages=data["total_pages"],
            search_query=search_query,
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin:users:search")
async def admin_users_search_prompt(
    callback: CallbackQuery,
    state: FSMContext,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    await state.set_state(AdminFlow.waiting_user_search)
    await message.edit_text(
        "🔍 <b>جستجوی کاربر</b>\n\n"
        "شناسه داخلی، Telegram ID یا نام کاربری را ارسال کن:\n"
        "مثال: <code>12345</code> | <code>987654321</code> | <code>@username</code>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin:users:clear-search")
async def admin_users_clear_search(
    callback: CallbackQuery,
    state: FSMContext,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    await state.update_data(user_search_query=None)
    admin_id = str(callback.from_user.id)
    data = await _load_users_page(api, admin_id, page=1)
    await message.edit_text(
        _users_list_text(data),
        reply_markup=admin_users_list_keyboard(
            data["users"],
            page=data["page"],
            total_pages=data["total_pages"],
        ),
        parse_mode="HTML",
    )
    await callback.answer("جستجو پاک شد")


@router.callback_query(F.data == "admin:users:jump")
async def admin_users_jump_prompt(
    callback: CallbackQuery,
    state: FSMContext,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    await state.set_state(AdminFlow.waiting_user_page_jump)
    await message.edit_text(
        "📄 شماره صفحه مورد نظر را ارسال کن:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminFlow.waiting_user_search)
async def admin_users_search_submit(
    message: Message,
    state: FSMContext,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    if not message.from_user or str(message.from_user.id) not in bot_config.admin_chat_ids:
        return
    query = (message.text or "").strip()
    await state.update_data(user_search_query=query or None)
    await state.set_state(None)
    admin_id = str(message.from_user.id)
    try:
        data = await _load_users_page(api, admin_id, page=1, search_query=query or None)
    except Exception as exc:
        if await handle_admin_api_error(message, exc):
            return
        raise
    await message.answer(
        _users_list_text(data, search_query=query or None),
        reply_markup=admin_users_list_keyboard(
            data["users"],
            page=data["page"],
            total_pages=data["total_pages"],
            search_query=query or None,
        ),
        parse_mode="HTML",
    )


@router.message(AdminFlow.waiting_user_page_jump)
async def admin_users_jump_submit(
    message: Message,
    state: FSMContext,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    if not message.from_user or str(message.from_user.id) not in bot_config.admin_chat_ids:
        return
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("⚠️ لطفاً یک عدد معتبر وارد کن.")
        return
    page = int(raw)
    state_data = await state.get_data()
    search_query = state_data.get("user_search_query")
    await state.set_state(None)
    admin_id = str(message.from_user.id)
    data = await _load_users_page(api, admin_id, page=page, search_query=search_query)
    page = min(max(page, 1), data["total_pages"])
    if page != data["page"]:
        data = await _load_users_page(api, admin_id, page=page, search_query=search_query)
    await message.answer(
        _users_list_text(data, search_query=search_query),
        reply_markup=admin_users_list_keyboard(
            data["users"],
            page=data["page"],
            total_pages=data["total_pages"],
            search_query=search_query,
        ),
        parse_mode="HTML",
    )


@router.callback_query(F.data.regexp(r"^admin:user:\d+$"))
async def admin_user_detail(
    callback: CallbackQuery,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    user_id = int(callback.data.rsplit(":", 1)[1])
    admin_id = str(callback.from_user.id)
    try:
        user = await api.get_admin_user_detail(admin_id, user_id)
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        raise
    await message.edit_text(
        _user_detail_text(user),
        reply_markup=admin_user_detail_keyboard(user),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:user:\d+:configs$"))
async def admin_user_configs(
    callback: CallbackQuery,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    user_id = int(callback.data.split(":")[2])
    admin_id = str(callback.from_user.id)
    try:
        configs = await api.list_admin_user_configs(admin_id, user_id)
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        raise
    if not configs:
        text = "📁 کانفیگی برای این کاربر ثبت نشده."
    else:
        text = f"📁 <b>کانفیگ‌های کاربر #{user_id}</b>\n\nیک کانفیگ را انتخاب کن:"
    await message.edit_text(
        text,
        reply_markup=admin_user_configs_keyboard(user_id, configs),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:user:\d+:cfg:[0-9]{10}$"))
async def admin_user_config_detail(
    callback: CallbackQuery,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    parts = callback.data.split(":")
    user_id = int(parts[2])
    config_id = parts[4]
    admin_id = str(callback.from_user.id)
    try:
        config = await api.get_admin_user_config_detail(admin_id, user_id, config_id)
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        raise
    await message.edit_text(
        _config_detail_text(config),
        reply_markup=admin_user_config_detail_keyboard(user_id, config),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:user:\d+:cfg:[0-9]{10}:(enable|disable|regen)$"))
async def admin_user_config_action(
    callback: CallbackQuery,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    parts = callback.data.split(":")
    user_id = int(parts[2])
    config_id = parts[4]
    action = parts[5]
    admin_id = str(callback.from_user.id)
    try:
        if action == "enable":
            config = await api.enable_admin_user_config(admin_id, user_id, config_id)
        elif action == "disable":
            config = await api.disable_admin_user_config(admin_id, user_id, config_id)
        else:
            config = await api.regenerate_admin_user_config(admin_id, user_id, config_id)
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        raise
    await message.edit_text(
        _config_detail_text(config),
        reply_markup=admin_user_config_detail_keyboard(user_id, config),
        parse_mode="HTML",
    )
    await callback.answer("✅ انجام شد")


@router.callback_query(F.data.regexp(r"^admin:user:\d+:(block|unblock)$"))
async def admin_user_block_toggle(
    callback: CallbackQuery,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    parts = callback.data.split(":")
    user_id = int(parts[2])
    action = parts[3]
    admin_id = str(callback.from_user.id)
    try:
        if action == "block":
            user = await api.block_admin_user(admin_id, user_id)
        else:
            user = await api.unblock_admin_user(admin_id, user_id)
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        raise
    await message.edit_text(
        _user_detail_text(user),
        reply_markup=admin_user_detail_keyboard(user),
        parse_mode="HTML",
    )
    await callback.answer("✅ انجام شد")


@router.callback_query(F.data.regexp(r"^admin:user:\d+:collab:add$"))
async def admin_user_collab_add_start(
    callback: CallbackQuery,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    user_id = int(callback.data.split(":")[2])
    await message.edit_text(
        "🤝 <b>افزودن همکار</b>\n\nمرحله ۱: درصد تخفیف را انتخاب کن:",
        reply_markup=admin_collaborator_discount_keyboard(user_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:user:\d+:collab:percent:\d+$"))
async def admin_user_collab_select_service(
    callback: CallbackQuery,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    parts = callback.data.split(":")
    user_id = int(parts[2])
    percent = int(parts[5])
    admin_id = str(callback.from_user.id)
    services = await api.list_service_types_admin(admin_id)
    await message.edit_text(
        f"🤝 <b>افزودن همکار</b>\n\n"
        f"مرحله ۲: نوع سرویس برای تخفیف <b>{percent}%</b> را انتخاب کن:",
        reply_markup=admin_collaborator_service_keyboard(user_id, percent, services),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:user:\d+:collab:svc:\d+:.+$"))
async def admin_user_collab_save(
    callback: CallbackQuery,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    parts = callback.data.split(":")
    user_id = int(parts[2])
    percent = int(parts[5])
    service_type = parts[6]
    admin_id = str(callback.from_user.id)
    try:
        user = await api.add_admin_user_collaborator(
            admin_id,
            user_id,
            discount_percent=percent,
            service_type=service_type,
        )
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        raise
    await message.edit_text(
        _user_detail_text(user),
        reply_markup=admin_user_detail_keyboard(user),
        parse_mode="HTML",
    )
    await callback.answer("✅ همکار ذخیره شد")


@router.callback_query(F.data.regexp(r"^admin:user:\d+:collab:remove$"))
async def admin_user_collab_remove(
    callback: CallbackQuery,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    user_id = int(callback.data.split(":")[2])
    admin_id = str(callback.from_user.id)
    try:
        user = await api.remove_admin_user_collaborator(admin_id, user_id)
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        raise
    await message.edit_text(
        _user_detail_text(user),
        reply_markup=admin_user_detail_keyboard(user),
        parse_mode="HTML",
    )
    await callback.answer("✅ همکار حذف شد")
