from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard(is_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🛒 خرید سرویس جدید", callback_data="menu:buy")],
        [InlineKeyboardButton(text="🔄 تمدید سرویس", callback_data="menu:renew")],
        [InlineKeyboardButton(text="💳 شارژ کیف پول", callback_data="menu:topup")],
        [InlineKeyboardButton(text="📦 سرویس‌های من", callback_data="menu:services")],
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
