"""Persian user-facing bot copy with emoji."""

STATUS_FA = {
    "active": "✅ فعال",
    "expired": "⏰ منقضی",
    "traffic_exceeded": "📊 حجم تمام شده",
    "disabled": "🚫 غیرفعال",
}

PURPOSE_FA = {
    "purchase": "🛒 خرید سرویس",
    "renewal": "🔄 تمدید",
    "topup": "💳 شارژ کیف پول",
}


def format_toman(amount: int) -> str:
    return f"{amount:,} تومان"


def welcome_message(user_id: int, balance: int) -> str:
    return (
        "🎉 <b>به ربات VPN خوش آمدید!</b>\n\n"
        "🚀 اینترنت <b>پرسرعت، امن و پایدار</b> — فقط چند ثانیه تا اتصال!\n"
        "🔒 بدون قطعی · ⚡ فعال‌سازی فوری · 💎 قیمت‌های ویژه\n\n"
        f"🆔 شناسه شما: <code>{user_id}</code>\n"
        f"💰 موجودی کیف پول: <b>{format_toman(balance)}</b>\n\n"
        "✨ <b>همین الان سرویس بخر</b> و بدون محدودیت وصل شو!\n"
        "👇 یک گزینه را انتخاب کن:"
    )


def main_menu_message(balance: int) -> str:
    return (
        "🏠 <b>منوی اصلی</b>\n\n"
        f"💰 موجودی کیف پول: <b>{format_toman(balance)}</b>\n\n"
        "🛒 برای خرید سریع، روی «خرید سرویس جدید» بزن!"
    )


def status_label_fa(label: str) -> str:
    return STATUS_FA.get(label, f"📌 {label}")
