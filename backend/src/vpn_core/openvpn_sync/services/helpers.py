def build_common_name(telegram_id: str, slot_index: int = 0) -> str:
    """Stable OpenVPN common name from Telegram chat id."""
    base = f"tg-{telegram_id}"
    if slot_index <= 0:
        return base
    return f"{base}-{slot_index}"


def node_api_configured(server) -> bool:
    return bool(server.openvpn.enabled and server.openvpn.node_api_secret)
