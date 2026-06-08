import secrets


def generate_config_id() -> str:
    """Return a unique 10-digit numeric OpenVPN client identifier."""
    return f"{secrets.randbelow(10**10):010d}"


def node_api_configured(server) -> bool:
    return bool(server.openvpn.enabled and server.openvpn.node_api_secret)
