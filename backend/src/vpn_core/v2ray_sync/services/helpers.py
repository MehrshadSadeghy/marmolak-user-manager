import secrets


def generate_config_id() -> str:
    """Return a unique 10-digit numeric V2Ray client identifier."""
    return f"{secrets.randbelow(10**10):010d}"


def node_api_configured(server) -> bool:
    return bool(server.v2ray.enabled and server.v2ray.node_api_secret)
