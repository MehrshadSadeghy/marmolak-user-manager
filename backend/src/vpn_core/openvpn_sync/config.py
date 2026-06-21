import logging
import os

from vpn_core.openvpn_sync.domain.auth_mode import OpenVpnAuthMode

LOGGER = logging.getLogger(__name__)


def get_openvpn_auth_mode() -> OpenVpnAuthMode:
    """Return configured OpenVPN server auth mode (default: certificate)."""
    raw = os.getenv("OPENVPN_AUTH_MODE", OpenVpnAuthMode.certificate.value).strip().lower()
    try:
        return OpenVpnAuthMode(raw)
    except ValueError:
        LOGGER.warning("Invalid OPENVPN_AUTH_MODE=%r; falling back to certificate", raw)
        return OpenVpnAuthMode.certificate


def get_server_auth_mode() -> OpenVpnAuthMode:
    """Auth mode applied to openvpn-node server.conf (migration window uses dual)."""
    return get_openvpn_auth_mode()


def get_provisioning_auth_mode() -> OpenVpnAuthMode:
    """Auth mode stored on newly provisioned credentials.

    During Phase 6 rollout, server runs in dual mode while new users receive user_pass
    credentials. Legacy rows keep their stored auth_mode unchanged.
    """
    explicit = os.getenv("OPENVPN_PROVISIONING_AUTH_MODE", "").strip().lower()
    if explicit:
        try:
            return OpenVpnAuthMode(explicit)
        except ValueError:
            LOGGER.warning(
                "Invalid OPENVPN_PROVISIONING_AUTH_MODE=%r; deriving from OPENVPN_AUTH_MODE",
                explicit,
            )

    server_mode = get_openvpn_auth_mode()
    if server_mode == OpenVpnAuthMode.dual:
        return OpenVpnAuthMode.user_pass
    return server_mode


def provisions_without_client_cert(auth_mode: OpenVpnAuthMode) -> bool:
    """Phase 8: user_pass provisioning stores auth-only profiles (no EasyRSA client cert)."""
    return auth_mode == OpenVpnAuthMode.user_pass


def get_openvpn_auto_apply_server_auth() -> bool:
    """When true, provisioning with dual/user_pass asks the node to patch server.conf."""
    return os.getenv("OPENVPN_AUTO_APPLY_SERVER_AUTH", "false").lower() in (
        "1",
        "true",
        "yes",
    )


def is_legacy_migration_enabled() -> bool:
    """When true, certificate-only users can opt in to username/password auth."""
    return os.getenv("OPENVPN_LEGACY_MIGRATION_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )


def get_legacy_migration_grace_days() -> int:
    """Minimum days after opt-in migration before cert-only profile can be finalized away."""
    raw = os.getenv("OPENVPN_LEGACY_MIGRATION_GRACE_DAYS", "7").strip()
    try:
        return max(int(raw), 0)
    except ValueError:
        LOGGER.warning("Invalid OPENVPN_LEGACY_MIGRATION_GRACE_DAYS=%r; using 7", raw)
        return 7
