from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard(is_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="Buy new service", callback_data="menu:buy")],
        [InlineKeyboardButton(text="Renew service", callback_data="menu:renew")],
        [InlineKeyboardButton(text="Wallet top-up", callback_data="menu:topup")],
        [InlineKeyboardButton(text="My services", callback_data="menu:services")],
        [InlineKeyboardButton(text="Support", callback_data="menu:support")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text="Admin panel", callback_data="menu:admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Back to menu", callback_data="menu:home")]]
    )


def services_keyboard(services: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=item["display_name"], callback_data=f"service:{item['slug']}")]
        for item in services
    ]
    rows.append([InlineKeyboardButton(text="Back to menu", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def plans_keyboard(plans: list[dict], prefix: str) -> InlineKeyboardMarkup:
    rows = []
    for plan in plans:
        gb = plan["traffic_limit_bytes"] / (1024**3)
        label = f"{plan['name']} — {gb:.0f} GB / {plan['duration_days']}d — {plan['price_toman']} Toman"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"{prefix}:plan:{plan['id']}")])
    rows.append([InlineKeyboardButton(text="Back", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment_methods_keyboard(methods: list[dict], prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=method["name"], callback_data=f"{prefix}:pay:{method['id']}")]
        for method in methods
    ]
    rows.append([InlineKeyboardButton(text="Back to menu", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def renew_services_keyboard(services: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for item in services:
        label = f"#{item['subscription_id']} {item['service_type']} — {item['status_label']}"
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=f"renew:sub:{item['subscription_id']}")]
        )
    rows.append([InlineKeyboardButton(text="Back to menu", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Pending payments", callback_data="admin:payments")],
            [InlineKeyboardButton(text="Service types", callback_data="admin:services")],
            [InlineKeyboardButton(text="Plans", callback_data="admin:plans")],
            [InlineKeyboardButton(text="Back to menu", callback_data="menu:home")],
        ]
    )


def admin_payment_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Approve",
                    callback_data=f"admin:approve:{payment_id}",
                ),
                InlineKeyboardButton(
                    text="Reject",
                    callback_data=f"admin:reject:{payment_id}",
                ),
            ]
        ]
    )


def admin_services_keyboard(services: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for item in services:
        state = "ON" if item["is_enabled"] else "OFF"
        action = "disable" if item["is_enabled"] else "enable"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{item['display_name']} [{state}]",
                    callback_data=f"admin:toggle:{action}:{item['slug']}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="Back", callback_data="menu:admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
