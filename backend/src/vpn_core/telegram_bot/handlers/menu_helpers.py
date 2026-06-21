from vpn_core.telegram_bot.client.api_client import UserManagerApiClient


async def pasarguard_menu_enabled(api: UserManagerApiClient) -> bool:
    try:
        settings = await api.get_pasarguard_panel_settings()
        return bool(settings.get("enabled"))
    except Exception:
        return False


async def pasarguard_webapp_url(api: UserManagerApiClient) -> str | None:
    try:
        settings = await api.get_pasarguard_panel_settings()
        if not settings.get("enabled"):
            return None
        return settings.get("webapp_url")
    except Exception:
        return None
