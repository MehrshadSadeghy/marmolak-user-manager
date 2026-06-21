from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


def main_menu_keyboard(is_admin: bool, *, pasarguard_enabled: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🛒 خرید سرویس جدید", callback_data="menu:buy")],
        [InlineKeyboardButton(text="🔄 تمدید سرویس", callback_data="menu:renew")],
        [InlineKeyboardButton(text="💳 شارژ کیف پول", callback_data="menu:topup")],
        [InlineKeyboardButton(text="📦 سرویس‌های من", callback_data="menu:services")],
        [InlineKeyboardButton(text="📊 استعلام حجم کانفیگ", callback_data="menu:config-traffic")],
        [InlineKeyboardButton(text="💬 پشتیبانی", callback_data="menu:support")],
    ]
    if pasarguard_enabled:
        rows.append(
            [InlineKeyboardButton(text="🔗 افزودن پنل پاسارگارد", callback_data="menu:pasarguard")]
        )
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


def plans_keyboard(
    plans: list[dict],
    prefix: str,
    *,
    back_callback: str = "menu:home",
) -> InlineKeyboardMarkup:
    rows = []
    for plan in plans:
        gb = plan["traffic_limit_bytes"] / (1024**3)
        price_label = f"{plan['price_toman']:,}ت"
        label = (
            f"⭐ {plan['name']} — {gb:.0f}GB / {plan['duration_days']}روز — "
            f"{price_label}"
        )
        rows.append([InlineKeyboardButton(text=label, callback_data=f"{prefix}:plan:{plan['id']}")])
    rows.append([InlineKeyboardButton(text="◀️ بازگشت", callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def openvpn_servers_purchase_keyboard(servers: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for server in servers:
        capacity = f"{server['current_users']}/{server['max_users']}"
        if server.get("is_full"):
            label = f"🔴 {server['name']} — پر ({capacity})"
            rows.append(
                [
                    InlineKeyboardButton(
                        text=label,
                        callback_data=f"buy:server-full:{server['id']}",
                    )
                ]
            )
        else:
            label = f"🟢 {server['name']} — {capacity} ظرفیت"
            rows.append(
                [
                    InlineKeyboardButton(
                        text=label,
                        callback_data=f"buy:server:{server['id']}",
                    )
                ]
            )
    rows.append([InlineKeyboardButton(text="◀️ بازگشت", callback_data="menu:buy")])
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


def user_services_keyboard(services: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for item in services:
        subscription_id = item["subscription_id"]
        if item.get("service_type") == "openvpn":
            config_ids = item.get("config_ids") or []
            migratable = set(item.get("migratable_config_ids") or [])
            finalizable = set(item.get("finalizable_config_ids") or [])
            password_configs = set(item.get("password_config_ids") or [])
            if config_ids:
                for config_id in config_ids:
                    rows.append(
                        [
                            InlineKeyboardButton(
                                text=f"📥 دریافت .ovpn — {config_id}",
                                callback_data=f"download:config:{config_id}",
                            )
                        ]
                    )
                    if config_id in migratable:
                        rows.append(
                            [
                                InlineKeyboardButton(
                                    text=f"🔐 ورود با نام کاربری/رمز — {config_id}",
                                    callback_data=f"credentials:migrate:{config_id}",
                                )
                            ]
                        )
                    if config_id in password_configs:
                        rows.append(
                            [
                                InlineKeyboardButton(
                                    text=f"ℹ️ اطلاعات اتصال — {config_id}",
                                    callback_data=f"credentials:view:{config_id}",
                                ),
                                InlineKeyboardButton(
                                    text=f"🔑 بازیابی رمز — {config_id}",
                                    callback_data=f"credentials:rotate:{config_id}",
                                ),
                            ]
                        )
                    if config_id in finalizable:
                        rows.append(
                            [
                                InlineKeyboardButton(
                                    text=f"✅ حذف گواهی قدیمی — {config_id}",
                                    callback_data=f"credentials:finalize:{config_id}",
                                )
                            ]
                        )
            else:
                rows.append(
                    [
                        InlineKeyboardButton(
                            text=f"📥 دریافت فایل .ovpn — #{subscription_id}",
                            callback_data=f"download:sub:{subscription_id}",
                        )
                    ]
                )
    rows.append([InlineKeyboardButton(text="🛒 خرید سرویس جدید", callback_data="menu:buy")])
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


def pasarguard_panel_keyboard(
    *,
    webapp_url: str | None,
    apps: list[dict] | None = None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if webapp_url and webapp_url.startswith("https://"):
        rows.append(
            [
                InlineKeyboardButton(
                    text="🎛 افزودن پنل پاسارگارد",
                    web_app=WebAppInfo(url=webapp_url),
                )
            ]
        )
    for app in apps or []:
        import_url = app.get("import_url")
        if not import_url:
            continue
        label = f"📲 {app.get('name', 'App')}"
        if app.get("recommended"):
            label = f"⭐ {app.get('name', 'App')}"
        rows.append([InlineKeyboardButton(text=label, url=import_url)])
    rows.append(
        [InlineKeyboardButton(text="📥 دریافت فایل OpenVPN", callback_data="pasarguard:openvpn")]
    )
    rows.append([InlineKeyboardButton(text="🏠 بازگشت به منو", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_menu_keyboard(*, pasarguard_webapp_url: str | None = None) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="👥 مدیریت کاربران", callback_data="admin:users")],
        [InlineKeyboardButton(text="⏳ پرداخت‌های در انتظار", callback_data="admin:payments")],
        [InlineKeyboardButton(text="🔧 انواع سرویس", callback_data="admin:services")],
        [InlineKeyboardButton(text="📋 پلن‌ها", callback_data="admin:plans")],
        [InlineKeyboardButton(text="💳 روش‌های پرداخت", callback_data="admin:payment-methods")],
        [InlineKeyboardButton(text="📊 گزارش مالی", callback_data="admin:report")],
        [InlineKeyboardButton(text="🖥 سرورها و ظرفیت", callback_data="admin:servers")],
        [InlineKeyboardButton(text="🔌 OpenVPN پورت/پروتکل", callback_data="admin:openvpn-endpoint")],
    ]
    if pasarguard_webapp_url and pasarguard_webapp_url.startswith("https://"):
        rows.append(
            [
                InlineKeyboardButton(
                    text="🎛 پنل پاسارگارد",
                    web_app=WebAppInfo(url=pasarguard_webapp_url),
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="🏠 بازگشت به منو", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


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


def _server_capacity_label(server: dict) -> str:
    capacity = f"{server['current_users']}/{server['max_users']}"
    if server.get("is_full"):
        return f"🔴 {server['name']} — پر ({capacity})"
    return f"🟢 {server['name']} — {capacity} ظرفیت"


def admin_openvpn_servers_keyboard(servers: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for server in servers:
        label = (
            f"{_server_capacity_label(server)} — "
            f"{server['vpn_proto'].upper()}/{server['vpn_port']} ({server['status']})"
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


def admin_users_list_keyboard(
    users: list[dict],
    *,
    page: int,
    total_pages: int,
    search_query: str | None = None,
) -> InlineKeyboardMarkup:
    rows = []
    for user in users:
        blocked = "🚫" if user.get("is_blocked") else "✅"
        collab = "🤝" if user.get("is_collaborator") else "👤"
        username = user.get("username") or "—"
        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{blocked}{collab} #{user['id']} | tg:{user['telegram_id']} | @{username}"
                    ),
                    callback_data=f"admin:user:{user['id']}",
                )
            ]
        )

    nav_row = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton(text="◀️ قبلی", callback_data=f"admin:users:page:{page - 1}")
        )
    nav_row.append(
        InlineKeyboardButton(text=f"📄 {page}/{total_pages}", callback_data="admin:users:jump")
    )
    if page < total_pages:
        nav_row.append(
            InlineKeyboardButton(text="بعدی ▶️", callback_data=f"admin:users:page:{page + 1}")
        )
    if nav_row:
        rows.append(nav_row)

    rows.append([InlineKeyboardButton(text="🔍 جستجو", callback_data="admin:users:search")])
    if search_query:
        rows.append(
            [InlineKeyboardButton(text="❌ پاک کردن جستجو", callback_data="admin:users:clear-search")]
        )
    rows.append([InlineKeyboardButton(text="◀️ بازگشت", callback_data="menu:admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_user_detail_keyboard(user: dict) -> InlineKeyboardMarkup:
    user_id = user["id"]
    rows = [
        [InlineKeyboardButton(text="📁 کانفیگ‌ها", callback_data=f"admin:user:{user_id}:configs")],
    ]
    if user.get("is_blocked"):
        rows.append(
            [InlineKeyboardButton(text="✅ رفع مسدودیت", callback_data=f"admin:user:{user_id}:unblock")]
        )
    else:
        rows.append(
            [InlineKeyboardButton(text="🚫 مسدود کردن", callback_data=f"admin:user:{user_id}:block")]
        )
    if user.get("is_collaborator"):
        rows.append(
            [
                InlineKeyboardButton(
                    text="❌ حذف همکار",
                    callback_data=f"admin:user:{user_id}:collab:remove",
                )
            ]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🤝 افزودن همکار",
                    callback_data=f"admin:user:{user_id}:collab:add",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="◀️ بازگشت", callback_data="admin:users")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_user_configs_keyboard(user_id: int, configs: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for config in configs:
        status = "🟢" if config.get("status") == "Active" else "🔴"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{status} {config['config_id']}",
                    callback_data=f"admin:user:{user_id}:cfg:{config['config_id']}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="◀️ بازگشت", callback_data=f"admin:user:{user_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_user_config_detail_keyboard(user_id: int, config: dict) -> InlineKeyboardMarkup:
    config_id = config["config_id"]
    rows = []
    if config.get("status") == "Active":
        rows.append(
            [
                InlineKeyboardButton(
                    text="🔴 غیرفعال",
                    callback_data=f"admin:user:{user_id}:cfg:{config_id}:disable",
                )
            ]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🟢 فعال",
                    callback_data=f"admin:user:{user_id}:cfg:{config_id}:enable",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="♻️ بازسازی کانفیگ",
                callback_data=f"admin:user:{user_id}:cfg:{config_id}:regen",
            )
        ]
    )
    rows.append([InlineKeyboardButton(text="◀️ بازگشت", callback_data=f"admin:user:{user_id}:configs")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_collaborator_discount_keyboard(user_id: int) -> InlineKeyboardMarkup:
    percents = [5, 10, 15, 20, 30]
    rows = [
        [
            InlineKeyboardButton(
                text=f"{percent}%",
                callback_data=f"admin:user:{user_id}:collab:percent:{percent}",
            )
        ]
        for percent in percents
    ]
    rows.append([InlineKeyboardButton(text="◀️ بازگشت", callback_data=f"admin:user:{user_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_collaborator_service_keyboard(user_id: int, percent: int, services: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=item["display_name"],
                callback_data=f"admin:user:{user_id}:collab:svc:{percent}:{item['slug']}",
            )
        ]
        for item in services
    ]
    rows.append([InlineKeyboardButton(text="◀️ بازگشت", callback_data=f"admin:user:{user_id}:collab:add")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
