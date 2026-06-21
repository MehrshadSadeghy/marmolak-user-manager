from enum import Enum


class OpenVpnAuthMode(str, Enum):
    """Controls how new OpenVPN credentials are provisioned."""

    certificate = "certificate"
    dual = "dual"
    user_pass = "user_pass"
