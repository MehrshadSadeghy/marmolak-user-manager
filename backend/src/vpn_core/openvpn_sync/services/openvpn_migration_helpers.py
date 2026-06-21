from datetime import UTC, datetime, timedelta

from vpn_core.openvpn_sync.config import (
    get_legacy_migration_grace_days,
    get_server_auth_mode,
    is_legacy_migration_enabled,
)
from vpn_core.openvpn_sync.domain.auth_mode import OpenVpnAuthMode
from vpn_core.openvpn_sync.domain.openvpn_client_credential import (
    OpenVpnClientCredential,
    OpenVpnConfigStatus,
)


def can_migrate_legacy_credential(credential: OpenVpnClientCredential) -> bool:
    if not is_legacy_migration_enabled():
        return False
    if credential.status != OpenVpnConfigStatus.active:
        return False
    if credential.auth_mode != OpenVpnAuthMode.certificate:
        return False
    return get_server_auth_mode() in {OpenVpnAuthMode.dual, OpenVpnAuthMode.user_pass}


def can_finalize_auth_migration(credential: OpenVpnClientCredential) -> bool:
    if not is_legacy_migration_enabled():
        return False
    if credential.status != OpenVpnConfigStatus.active:
        return False
    if credential.auth_mode != OpenVpnAuthMode.dual:
        return False
    if not credential.password_hash:
        return False

    grace_days = get_legacy_migration_grace_days()
    if grace_days == 0:
        return True

    migrated_at = credential.auth_synced_at or credential.password_rotated_at
    if not migrated_at:
        return False
    return datetime.now(UTC) >= migrated_at + timedelta(days=grace_days)
