from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from vpn_core.telegram_bot.client.api_client import UserManagerApiClient
from vpn_core.telegram_bot.config import TelegramBotConfig
from vpn_core.telegram_bot.handlers.common import guard_admin_callback, handle_admin_api_error, edit_callback_message
from vpn_core.telegram_bot.keyboards.main import (
    admin_menu_keyboard,
    admin_openvpn_confirm_keyboard,
    admin_openvpn_proto_keyboard,
    admin_openvpn_servers_keyboard,
)
from vpn_core.telegram_bot.states import AdminFlow

router = Router()


def _format_server_capacity_lines(servers: list[dict]) -> list[str]:
    lines = []
    for server in servers:
        capacity = f"{server['current_users']}/{server['max_users']}"
        status = "🔴 پر" if server.get("is_full") else f"🟢 {server['remaining_slots']} ظرفیت باقی"
        lines.append(
            f"• <b>{server['name']}</b>\n"
            f"  👥 {capacity} | {status}\n"
            f"  🔌 {server['vpn_proto'].upper()}/{server['vpn_port']} | وضعیت: {server['status']}"
        )
    return lines


@router.callback_query(F.data == "admin:servers")
async def admin_servers_capacity(
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
        servers = await api.list_openvpn_servers_admin(str(callback.from_user.id))
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        raise
    if not servers:
        await edit_callback_message(message, 
            "⚠️ سرور OpenVPN فعالی یافت نشد.\n"
            "ابتدا سرور را در user-manager با openvpn.enabled=true ثبت کن.",
            reply_markup=admin_menu_keyboard(),
            parse_mode="HTML",
        )
    else:
        lines = _format_server_capacity_lines(servers)
        await edit_callback_message(message, 
            "🖥 <b>سرورها و ظرفیت</b>\n\n"
            "تعداد کانفیگ‌های فعال هر سرور به‌صورت زنده از دیتابیس خوانده می‌شود.\n\n"
            + "\n\n".join(lines),
            reply_markup=admin_menu_keyboard(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "admin:openvpn-endpoint")
async def admin_openvpn_endpoint_menu(
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
        servers = await api.list_openvpn_servers_admin(str(callback.from_user.id))
    except Exception as exc:
        if await handle_admin_api_error(callback, exc):
            return
        raise
    if not servers:
        await edit_callback_message(message, 
            "⚠️ سرور OpenVPN فعالی یافت نشد.\n"
            "ابتدا سرور را در user-manager با openvpn.enabled=true ثبت کن.",
            reply_markup=admin_menu_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()
        return
    await edit_callback_message(message, 
        "🔌 <b>تغییر پورت/پروتکل OpenVPN</b>\n\n"
        "سرور مورد نظر را انتخاب کن:",
        reply_markup=admin_openvpn_servers_keyboard(servers),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:ovpn:server:"))
async def admin_openvpn_select_server(
    callback: CallbackQuery,
    bot_config: TelegramBotConfig,
    state: FSMContext,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    server_id = int(callback.data.rsplit(":", 1)[1])
    await state.update_data(server_id=server_id)
    await edit_callback_message(message, 
        "🔌 پروتکل جدید را انتخاب کن:",
        reply_markup=admin_openvpn_proto_keyboard(server_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:ovpn:proto:"))
async def admin_openvpn_select_proto(
    callback: CallbackQuery,
    bot_config: TelegramBotConfig,
    state: FSMContext,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    _, _, _, server_id, proto = callback.data.split(":", 4)
    await state.update_data(server_id=int(server_id), proto=proto)
    await state.set_state(AdminFlow.openvpn_endpoint_port)
    await edit_callback_message(message, 
        f"🔢 پورت جدید را برای <b>{proto.upper()}</b> وارد کن (مثلاً 443 یا 10023):",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminFlow.openvpn_endpoint_port)
async def admin_openvpn_enter_port(
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

    text = message.text.strip()
    if not text.isdigit():
        await message.answer("⚠️ فقط عدد پورت را وارد کن (مثلاً 443).")
        return

    port = int(text)
    if not 1 <= port <= 65535:
        await message.answer("⚠️ پورت باید بین 1 تا 65535 باشد.")
        return

    data = await state.get_data()
    server_id = data.get("server_id")
    proto = data.get("proto")
    if not server_id or not proto:
        await state.clear()
        await message.answer("⚠️ جلسه منقضی شد. دوباره از پنل مدیریت شروع کن.")
        return

    try:
        servers = await api.list_openvpn_servers_admin(str(message.from_user.id))
    except Exception as exc:
        await message.answer(f"❌ خطا در دریافت سرورها: {exc}")
        return

    server = next((item for item in servers if item["id"] == server_id), None)
    server_name = server["name"] if server else f"#{server_id}"
    current = (
        f"{server['vpn_proto'].upper()}/{server['vpn_port']}" if server else "نامشخص"
    )

    await state.update_data(port=port, server_name=server_name, current_endpoint=current)
    await message.answer(
        "🔌 <b>تأیید تغییر OpenVPN</b>\n\n"
        f"🖥 سرور: <b>{server_name}</b>\n"
        f"📍 فعلی: <code>{current}</code>\n"
        f"🆕 جدید: <code>{proto.upper()}/{port}</code>\n\n"
        "با تأیید، این کارها خودکار انجام می‌شود:\n"
        "• به‌روزرسانی user-manager\n"
        "• به‌روزرسانی open-node\n"
        "• ویرایش server.conf\n"
        "• باز کردن پورت در فایروال (در صورت فعال بودن ufw)\n"
        "• ری‌استارت OpenVPN\n\n"
        "کانفیگ‌های جدید bot از این به بعد با پورت/پروتکل جدید ساخته می‌شوند.",
        reply_markup=admin_openvpn_confirm_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin:ovpn:confirm")
async def admin_openvpn_confirm(
    callback: CallbackQuery,
    api: UserManagerApiClient,
    bot_config: TelegramBotConfig,
    state: FSMContext,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return

    data = await state.get_data()
    server_id = data.get("server_id")
    port = data.get("port")
    proto = data.get("proto")
    server_name = data.get("server_name", f"#{server_id}")
    if not all([server_id, port, proto]):
        await state.clear()
        await callback.answer("⚠️ اطلاعات ناقص است", show_alert=True)
        return

    await edit_callback_message(message, "⏳ در حال اعمال تغییرات...")
    await callback.answer()
    try:
        result = await api.apply_openvpn_endpoint_admin(
            str(callback.from_user.id),
            int(server_id),
            int(port),
            str(proto),
        )
    except Exception as exc:
        await state.clear()
        if await handle_admin_api_error(callback, exc):
            return
        await edit_callback_message(message, 
            f"❌ خطا در اعمال تغییرات:\n<code>{exc}</code>",
            reply_markup=admin_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    await state.clear()
    status_icon = "✅" if result.get("openvpn_running") else "⚠️"
    await edit_callback_message(message, 
        f"{status_icon} <b>تغییر OpenVPN اعمال شد</b>\n\n"
        f"🖥 سرور: <b>{server_name}</b>\n"
        f"📍 قبلی: <code>{result['previous_proto'].upper()}/{result['previous_port']}</code>\n"
        f"🆕 جدید: <code>{result['proto'].upper()}/{result['port']}</code>\n\n"
        f"OpenVPN running: {'بله' if result.get('openvpn_running') else 'خیر'}\n"
        f"server.conf: {'✅' if result.get('server_conf_updated') else '—'}\n"
        f"ufw: {'✅' if result.get('firewall_rule_added') else '—'}\n"
        f"open-node env: {'✅' if result.get('env_file_updated') else '—'}\n\n"
        f"{result.get('message', '')}\n\n"
        "کاربران باید فایل .ovpn جدید از bot دریافت کنند.",
        reply_markup=admin_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin:ovpn:cancel")
async def admin_openvpn_cancel(
    callback: CallbackQuery,
    bot_config: TelegramBotConfig,
    state: FSMContext,
) -> None:
    message = callback.message
    if not message or not await guard_admin_callback(callback, bot_config):
        return
    await state.clear()
    await edit_callback_message(message, 
        "❌ تغییر OpenVPN لغو شد.",
        reply_markup=admin_menu_keyboard(),
    )
    await callback.answer()
