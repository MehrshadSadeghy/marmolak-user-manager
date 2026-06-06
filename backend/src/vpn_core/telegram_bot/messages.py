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

PERIOD_FA = {
    "daily": "روزانه",
    "weekly": "هفتگی",
    "monthly": "ماهانه",
}


def format_payment_method_display(method: dict) -> str:
    parts = [f"🏦 <b>{method['name']}</b>"]
    cards = method.get("card_numbers") or []
    if cards:
        parts.append("💳 <b>شماره کارت‌ها:</b>")
        for index, card in enumerate(cards, 1):
            parts.append(f"{index}. <code>{card.strip()}</code>")
    instructions = (method.get("instructions") or "").strip()
    if instructions:
        parts.append(instructions)
    return "\n".join(parts)


def format_financial_report(report: dict) -> str:
    period = PERIOD_FA.get(report["period"], report["period"])
    start_at = str(report["start_at"])[:10]
    end_at = str(report["end_at"])[:10]
    lines = [
        f"📊 <b>گزارش مالی {period}</b>",
        f"📅 از {start_at} تا {end_at}",
        "",
        f"💰 درآمد کل: <b>{format_toman(report['total_income_toman'])}</b>",
        "",
        "💳 <b>پرداخت‌های دستی (تأیید شده)</b>",
        (
            f"  تعداد: {report['manual_payments_count']} | "
            f"جمع: {format_toman(report['manual_payments_total_toman'])}"
        ),
    ]
    for purpose, breakdown in (report.get("manual_payments_by_purpose") or {}).items():
        label = PURPOSE_FA.get(purpose, purpose)
        lines.append(
            f"  • {label}: {breakdown['count']} — {format_toman(breakdown['total_toman'])}"
        )
    lines.extend(
        [
            "",
            "🛒 <b>فروش از کیف پول</b>",
            (
                f"  تعداد: {report['wallet_sales_count']} | "
                f"جمع: {format_toman(report['wallet_sales_total_toman'])}"
            ),
            "",
            "💵 <b>شارژ کیف پول</b>",
            (
                f"  تعداد: {report['wallet_topups_count']} | "
                f"جمع: {format_toman(report['wallet_topups_total_toman'])}"
            ),
            "",
            "⏳ <b>در انتظار تأیید</b>",
            (
                f"  تعداد: {report['pending_approval_count']} | "
                f"جمع: {format_toman(report['pending_approval_total_toman'])}"
            ),
        ]
    )
    return "\n".join(lines)
