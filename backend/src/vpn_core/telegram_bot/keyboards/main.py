from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard(is_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🛒 خرید سرویس جدید", callback_data="menu:buy")],
        [InlineKeyboardButton(text="🔄 تمدید سرویس", callback_data="menu:renew")],
        [InlineKeyboardButton(text="💳 شارژ کیف پول", callback_data="menu:topup")],
        [InlineKeyboardButton(text="📦 سرویس‌های من", callback_data="menu:services")],
        [InlineKeyboardButton(text="📊 استعلام حجم کانفیگ", callback_data="menu:config-traffic")],
        [InlineKeyboardButton(text="💬 پشتیبانی", callback_data="menu:support")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text="⚙️ پنل مدیریت", callback_data="menu:admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🏠 بازگشت به منو", callback_data="menu:home")]]
    )


def buy_now_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 خرید سرویس الان!", callback_data="menu:buy")],
            [InlineKeyboardButton(text="🏠 بازگشت به منو", callback_data="menu:home")],
        ]
    )


def services_keyboard(services: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"🔐 {item['display_name']}",
                callback_data=f"service:{item['slug']}",
            )
        ]
        for item in services
    ]
    rows.append([InlineKeyboardButton(text="🏠 بازگشت به منو", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def plans_keyboard(plans: list[dict], prefix: str) -> InlineKeyboardMarkup:
    rows = []
    for plan in plans:
        gb = plan["traffic_limit_bytes"] / (1024**3)
        label = (
            f"⭐ {plan['name']} — {gb:.0f}GB / {plan['duration_days']}روز — "
            f"{plan['price_toman']:,}ت"
        )
        rows.append([InlineKeyboardButton(text=label, callback_data=f"{prefix}:plan:{plan['id']}")])
    rows.append([InlineKeyboardButton(text="◀️ بازگشت", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment_methods_keyboard(methods: list[dict], prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"💳 {method['name']}",
                callback_data=f"{prefix}:pay:{method['id']}",
            )
        ]
        for method in methods
    ]
    rows.append([InlineKeyboardButton(text="🏠 بازگشت به منو", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def renew_services_keyboard(services: list[dict]) -> InlineKeyboardMarkup:
    from vpn_core.telegram_bot.messages import status_label_fa

    rows = []
    for item in services:
        status = status_label_fa(item["status_label"])
        label = f"#{item['subscription_id']} {item['service_type']} — {status}"
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=f"renew:sub:{item['subscription_id']}")]
        )
    rows.append([InlineKeyboardButton(text="🏠 بازگشت به منو", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏳ پرداخت‌های در انتظار", callback_data="admin:payments")],
            [InlineKeyboardButton(text="🔧 انواع سرویس", callback_data="admin:services")],
            [InlineKeyboardButton(text="📋 پلن‌ها", callback_data="admin:plans")],
            [InlineKeyboardButton(text="💳 روش‌های پرداخت", callback_data="admin:payment-methods")],
            [InlineKeyboardButton(text="📊 گزارش مالی", callback_data="admin:report")],
            [InlineKeyboardButton(text="🔌 OpenVPN پورت/پروتکل", callback_data="admin:openvpn-endpoint")],
            [InlineKeyboardButton(text="🏠 بازگشت به منو", callback_data="menu:home")],
        ]
    )


def admin_payment_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تأیید",
                    callback_data=f"admin:approve:{payment_id}",
                ),
                InlineKeyboardButton(
                    text="❌ رد",
                    callback_data=f"admin:reject:{payment_id}",
                ),
            ]
        ]
    )


def admin_services_keyboard(services: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for item in services:
        state = "🟢 روشن" if item["is_enabled"] else "🔴 خاموش"
        action = "disable" if item["is_enabled"] else "enable"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{item['display_name']} [{state}]",
                    callback_data=f"admin:toggle:{action}:{item['slug']}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="◀️ بازگشت", callback_data="menu:admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def admin_plans_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ افزودن پلن", callback_data="admin:plan:add")],
            [InlineKeyboardButton(text="◀️ بازگشت", callback_data="menu:admin")],
        ]
    )


def admin_plan_service_types_keyboard(services: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=item["display_name"],
                callback_data=f"admin:plan:add:type:{item['slug']}",
            )
        ]
        for item in services
    ]
    rows.append([InlineKeyboardButton(text="◀️ بازگشت", callback_data="admin:plans")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_payment_methods_keyboard(methods: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for method in methods:
        state = "🟢" if method.get("is_active", True) else "🔴"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{state} {method['name']}",
                    callback_data=f"admin:pm:{method['id']}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="➕ افزودن روش پرداخت", callback_data="admin:pm:add")])
    rows.append([InlineKeyboardButton(text="◀️ بازگشت", callback_data="menu:admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_payment_method_detail_keyboard(method_id: int, *, is_active: bool) -> InlineKeyboardMarkup:
    toggle_text = "🔴 غیرفعال کردن" if is_active else "🟢 فعال کردن"
    toggle_action = "disable" if is_active else "enable"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=toggle_text,
                    callback_data=f"admin:pm:toggle:{toggle_action}:{method_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 حذف",
                    callback_data=f"admin:pm:delete:{method_id}",
                )
            ],
            [InlineKeyboardButton(text="◀️ بازگشت", callback_data="admin:payment-methods")],
        ]
    )


def admin_report_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 روزانه", callback_data="admin:report:daily"),
                InlineKeyboardButton(text="📆 هفتگی", callback_data="admin:report:weekly"),
            ],
            [InlineKeyboardButton(text="🗓 ماهانه", callback_data="admin:report:monthly")],
            [InlineKeyboardButton(text="◀️ بازگشت", callback_data="menu:admin")],
        ]
    )


def admin_openvpn_servers_keyboard(servers: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for server in servers:
        label = (
            f"{server['name']} — {server['vpn_proto'].upper()}/{server['vpn_port']} "
            f"({server['status']})"
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"admin:ovpn:server:{server['id']}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="◀️ بازگشت", callback_data="menu:admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_openvpn_proto_keyboard(server_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="UDP", callback_data=f"admin:ovpn:proto:{server_id}:udp"),
                InlineKeyboardButton(text="TCP", callback_data=f"admin:ovpn:proto:{server_id}:tcp"),
            ],
            [InlineKeyboardButton(text="◀️ بازگشت", callback_data="admin:openvpn-endpoint")],
        ]
    )


def admin_openvpn_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ تأیید و اعمال", callback_data="admin:ovpn:confirm"),
                InlineKeyboardButton(text="❌ لغو", callback_data="admin:ovpn:cancel"),
            ]
        ]
    )
