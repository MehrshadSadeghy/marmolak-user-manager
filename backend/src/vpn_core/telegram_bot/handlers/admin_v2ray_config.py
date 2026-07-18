from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.config import TelegramBotConfig
from vpn_core.telegram_bot.handlers.common import guard_admin_callback, handle_admin_api_error, edit_callback_message
from vpn_core.telegram_bot.keyboards.main import (
    admin_menu_keyboard,
    admin_v2ray_choice_keyboard,
    admin_v2ray_config_keyboard,
    admin_v2ray_servers_keyboard,
)
from vpn_core.telegram_bot.states import AdminFlow

router = Router()

PROTOCOL_OPTIONS = [
    ("VLESS", "vless"),
    ("VMess", "vmess"),
    ("Trojan", "trojan"),
    ("Shadowsocks", "shadowsocks"),
]
NETWORK_OPTIONS = [
    ("TCP", "tcp"),
    ("WebSocket", "ws"),
    ("gRPC", "grpc"),
]
SECURITY_OPTIONS = [
    ("None", "none"),
    ("TLS", "tls"),
]


def _format_inbound_config(config: dict) -> str:
    return (
        f"🖥 <b>{config['server_name']}</b> (#{config['server_id']})\n\n"
        f"🔁 پروتکل: <code>{config['protocol']}</code>\n"
        f"🌐 Network: <code>{config['network']}</code>\n"
        f"🔒 Security: <code>{config['security']}</code>\n"
        f"🔢 Port: <code>{config['port']}</code>\n"
        f"👂 Listen: <code>{config['listen']}</code>\n"
        f"🌍 Host: <code>{config['server_host']}</code>\n"
        f"📂 WS Path: <code>{config.get('ws_path') or '—'}</code>\n"
        f"🏷 Tag: <code>{config['inbound_tag']}</code>"
    )


async def _show_server_config(
    message,
    api: UserManagerApiClient,
    admin_id: str,
    server_id: int,
) -> None:
    config = await api.get_v2ray_inbound_config_admin(admin_id, server_id)
    await edit_callback_message(
        message,
        "⚡ <b>تنظیمات V2Ray / Xray</b>\n\n"
        + _format_inbound_config(config)
        + "\n\n👇 مورد مورد نظر را برای ویرایش انتخاب کن:",
        reply_markup=admin_v2ray_config_keyboard(server_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin:v2ray-inbound")
async def admin_v2ray_inbound_menu(
    callback: CallbackQuery,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
    state: FSMContext,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    await state.clear()
    try:
        servers = await api.list_v2ray_servers_admin(str(callback.from_user.id))
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        raise
    if not servers:
        await edit_callback_message(
            message,
            "⚠️ سرور V2Ray فعالی یافت نشد.\n"
            "ابتدا سرور را با v2ray.enabled=true ثبت کن.",
            reply_markup=admin_menu_keyboard(),
            parse_mode="HTML",
        )
    else:
        await edit_callback_message(
            message,
            "⚡ <b>تنظیمات V2Ray / Xray</b>\n\n"
            "سروری که می‌خواهی تنظیمات inbound آن را مدیریت کنی انتخاب کن:",
            reply_markup=admin_v2ray_servers_keyboard(servers),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:v2ray:server:"))
async def admin_v2ray_select_server(
    callback: CallbackQuery,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
    state: FSMContext,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    server_id = int(callback.data.rsplit(":", 1)[1])
    await state.update_data(server_id=server_id)
    try:
        await _show_server_config(message, api, str(callback.from_user.id), server_id)
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        raise
    await callback.answer()


@router.callback_query(F.data.startswith("admin:v2ray:refresh:"))
async def admin_v2ray_refresh_config(
    callback: CallbackQuery,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    server_id = int(callback.data.rsplit(":", 1)[1])
    try:
        await _show_server_config(message, api, str(callback.from_user.id), server_id)
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        raise
    await callback.answer("🔄 بروزرسانی شد")


@router.callback_query(F.data.startswith("admin:v2ray:edit:protocol:"))
async def admin_v2ray_edit_protocol(callback: CallbackQuery, bot_config: TelegramBotConfig) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    server_id = int(callback.data.rsplit(":", 1)[1])
    await edit_callback_message(
        message,
        "🔁 پروتکل جدید را انتخاب کن:",
        reply_markup=admin_v2ray_choice_keyboard(server_id, "protocol", PROTOCOL_OPTIONS),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:v2ray:edit:network:"))
async def admin_v2ray_edit_network(callback: CallbackQuery, bot_config: TelegramBotConfig) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    server_id = int(callback.data.rsplit(":", 1)[1])
    await edit_callback_message(
        message,
        "🌐 Network جدید را انتخاب کن:",
        reply_markup=admin_v2ray_choice_keyboard(server_id, "network", NETWORK_OPTIONS),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:v2ray:edit:security:"))
async def admin_v2ray_edit_security(callback: CallbackQuery, bot_config: TelegramBotConfig) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    server_id = int(callback.data.rsplit(":", 1)[1])
    await edit_callback_message(
        message,
        "🔒 Security جدید را انتخاب کن:",
        reply_markup=admin_v2ray_choice_keyboard(server_id, "security", SECURITY_OPTIONS),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:v2ray:edit:port:"))
async def admin_v2ray_edit_port(
    callback: CallbackQuery,
    bot_config: TelegramBotConfig,
    state: FSMContext,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    server_id = int(callback.data.rsplit(":", 1)[1])
    await state.update_data(server_id=server_id, v2ray_field="port")
    await state.set_state(AdminFlow.v2ray_inbound_port)
    await edit_callback_message(message, "🔢 پورت جدید را وارد کن (مثلاً 443):")
    await callback.answer()


@router.callback_query(F.data.startswith("admin:v2ray:edit:wspath:"))
async def admin_v2ray_edit_ws_path(
    callback: CallbackQuery,
    bot_config: TelegramBotConfig,
    state: FSMContext,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    server_id = int(callback.data.rsplit(":", 1)[1])
    await state.update_data(server_id=server_id, v2ray_field="ws_path")
    await state.set_state(AdminFlow.v2ray_inbound_ws_path)
    await edit_callback_message(message, "📂 WS Path جدید را وارد کن (مثلاً /v2ray):")
    await callback.answer()


@router.callback_query(F.data.startswith("admin:v2ray:edit:host:"))
async def admin_v2ray_edit_host(
    callback: CallbackQuery,
    bot_config: TelegramBotConfig,
    state: FSMContext,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    server_id = int(callback.data.rsplit(":", 1)[1])
    await state.update_data(server_id=server_id, v2ray_field="server_host")
    await state.set_state(AdminFlow.v2ray_inbound_server_host)
    await edit_callback_message(message, "🌍 Server Host جدید را وارد کن (دامنه یا IP):")
    await callback.answer()


@router.callback_query(F.data.startswith("admin:v2ray:set:"))
async def admin_v2ray_apply_choice(
    callback: CallbackQuery,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
    state: FSMContext,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    _, _, _, field, server_id, value = callback.data.split(":", 5)
    await edit_callback_message(message, "⏳ در حال اعمال...")
    await callback.answer()
    try:
        result = await api.patch_v2ray_inbound_config_admin(
            str(callback.from_user.id),
            int(server_id),
            {field: value},
        )
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        await edit_callback_message(
            message,
            f"❌ خطا در اعمال تنظیمات:\n<code>{exc}</code>",
            reply_markup=admin_menu_keyboard(),
            parse_mode="HTML",
        )
        return
    await state.clear()
    await edit_callback_message(
        message,
        "✅ <b>تنظیمات V2Ray اعمال شد</b>\n\n"
        f"{result.get('message', '')}\n\n"
        "⚠️ کاربران باید لینک اشتراک یا کانفیگ جدید دریافت کنند.",
        reply_markup=admin_v2ray_config_keyboard(int(server_id)),
        parse_mode="HTML",
    )
    try:
        await _show_server_config(message, api, str(callback.from_user.id), int(server_id))
    except Exception:
        pass


@router.message(AdminFlow.v2ray_inbound_port)
async def admin_v2ray_apply_port(
    message: Message,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
    state: FSMContext,
) -> None:
    if not message.from_user or not message.text:
        return
    if str(message.from_user.id) not in bot_config.admin_chat_ids:
        await message.answer("⛔ دسترسی ادمین ندارید.")
        return
    if not message.text.strip().isdigit():
        await message.answer("⚠️ فقط عدد پورت را وارد کن.")
        return
    port = int(message.text.strip())
    if not 1 <= port <= 65535:
        await message.answer("⚠️ پورت باید بین 1 تا 65535 باشد.")
        return
    data = await state.get_data()
    server_id = data.get("server_id")
    if not server_id:
        await state.clear()
        await message.answer("⚠️ جلسه منقضی شد.")
        return
    try:
        result = await api.patch_v2ray_inbound_config_admin(
            str(message.from_user.id),
            int(server_id),
            {"port": port},
        )
    except Exception as exc:
        await state.clear()
        await message.answer(f"❌ خطا: {exc}")
        return
    await state.clear()
    await message.answer(
        f"✅ پورت به <code>{port}</code> تغییر کرد.\n{result.get('message', '')}",
        reply_markup=admin_v2ray_config_keyboard(int(server_id)),
        parse_mode="HTML",
    )


@router.message(AdminFlow.v2ray_inbound_ws_path)
async def admin_v2ray_apply_ws_path(
    message: Message,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
    state: FSMContext,
) -> None:
    if not message.from_user or not message.text:
        return
    if str(message.from_user.id) not in bot_config.admin_chat_ids:
        await message.answer("⛔ دسترسی ادمین ندارید.")
        return
    ws_path = message.text.strip()
    if not ws_path.startswith("/"):
        await message.answer("⚠️ مسیر باید با / شروع شود.")
        return
    data = await state.get_data()
    server_id = data.get("server_id")
    if not server_id:
        await state.clear()
        await message.answer("⚠️ جلسه منقضی شد.")
        return
    try:
        result = await api.patch_v2ray_inbound_config_admin(
            str(message.from_user.id),
            int(server_id),
            {"ws_path": ws_path},
        )
    except Exception as exc:
        await state.clear()
        await message.answer(f"❌ خطا: {exc}")
        return
    await state.clear()
    await message.answer(
        f"✅ WS Path به <code>{ws_path}</code> تغییر کرد.\n{result.get('message', '')}",
        reply_markup=admin_v2ray_config_keyboard(int(server_id)),
        parse_mode="HTML",
    )


@router.message(AdminFlow.v2ray_inbound_server_host)
async def admin_v2ray_apply_server_host(
    message: Message,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
    state: FSMContext,
) -> None:
    if not message.from_user or not message.text:
        return
    if str(message.from_user.id) not in bot_config.admin_chat_ids:
        await message.answer("⛔ دسترسی ادمین ندارید.")
        return
    server_host = message.text.strip()
    if not server_host:
        await message.answer("⚠️ host نامعتبر است.")
        return
    data = await state.get_data()
    server_id = data.get("server_id")
    if not server_id:
        await state.clear()
        await message.answer("⚠️ جلسه منقضی شد.")
        return
    try:
        result = await api.patch_v2ray_inbound_config_admin(
            str(message.from_user.id),
            int(server_id),
            {"server_host": server_host},
        )
    except Exception as exc:
        await state.clear()
        await message.answer(f"❌ خطا: {exc}")
        return
    await state.clear()
    await message.answer(
        f"✅ Server Host به <code>{server_host}</code> تغییر کرد.\n{result.get('message', '')}",
        reply_markup=admin_v2ray_config_keyboard(int(server_id)),
        parse_mode="HTML",
    )
