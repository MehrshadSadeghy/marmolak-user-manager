from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from vpn_core.openvpn_sync.domain.auth_mode import OpenVpnAuthMode
from vpn_core.openvpn_sync.domain.openvpn_client_credential import (
    OpenVpnClientCredential,
    OpenVpnConfigStatus,
)
from vpn_core.openvpn_sync.services.openvpn_migration_helpers import (
    can_finalize_auth_migration,
    can_migrate_legacy_credential,
)
from vpn_core.openvpn_sync.services.openvpn_provisioning_service import OpenVpnProvisioningService
from vpn_core.openvpn_sync.services.password_service import PasswordService
from vpn_core.server_management_domain.domain.capacity import ServerCapacity
from vpn_core.server_management_domain.domain.connection_info import ConnectionInfo
from vpn_core.server_management_domain.domain.openvpn_settings import OpenVpnSettings
from vpn_core.server_management_domain.domain.server import Server


def _credential(*, auth_mode: OpenVpnAuthMode = OpenVpnAuthMode.certificate) -> OpenVpnClientCredential:
    return OpenVpnClientCredential(
        id=1,
        user_id=42,
        subscription_id=7,
        server_id=1,
        telegram_id="123456789",
        common_name="0123456789",
        ovpn_content="<ca>real</ca><cert>x</cert>",
        auth_mode=auth_mode,
        vpn_username="0123456789" if auth_mode != OpenVpnAuthMode.certificate else None,
        status=OpenVpnConfigStatus.active,
    )


def test_can_migrate_legacy_requires_flag_and_dual_server(monkeypatch):
    monkeypatch.setenv("OPENVPN_LEGACY_MIGRATION_ENABLED", "true")
    monkeypatch.setenv("OPENVPN_AUTH_MODE", "dual")
    assert can_migrate_legacy_credential(_credential()) is True


def test_can_migrate_legacy_rejects_already_migrated(monkeypatch):
    monkeypatch.setenv("OPENVPN_LEGACY_MIGRATION_ENABLED", "true")
    monkeypatch.setenv("OPENVPN_AUTH_MODE", "dual")
    assert can_migrate_legacy_credential(_credential(auth_mode=OpenVpnAuthMode.dual)) is False


def test_can_finalize_requires_grace_period(monkeypatch):
    monkeypatch.setenv("OPENVPN_LEGACY_MIGRATION_ENABLED", "true")
    monkeypatch.setenv("OPENVPN_LEGACY_MIGRATION_GRACE_DAYS", "7")
    credential = _credential(auth_mode=OpenVpnAuthMode.dual)
    credential.password_hash = "$2b$04$hash"
    credential.auth_synced_at = datetime.now(UTC) - timedelta(days=1)
    assert can_finalize_auth_migration(credential) is False

    credential.auth_synced_at = datetime.now(UTC) - timedelta(days=8)
    assert can_finalize_auth_migration(credential) is True


def _server() -> Server:
    return Server(
        id=1,
        name="node-1",
        country_code="DE",
        cpu_cores=2,
        ram_mb=2048,
        disk_gb=40,
        connection=ConnectionInfo(host="10.0.0.1", api_port=8090),
        capacity=ServerCapacity(max_bandwidth_mbps=1000, max_users=100),
        openvpn=OpenVpnSettings(enabled=True, node_api_secret="secret", vpn_host="vpn.example.com"),
    )


@pytest.mark.asyncio
async def test_migrate_legacy_to_auth_sets_dual_and_returns_password(monkeypatch):
    monkeypatch.setenv("OPENVPN_LEGACY_MIGRATION_ENABLED", "true")
    monkeypatch.setenv("OPENVPN_AUTH_MODE", "dual")

    credential = _credential()
    credential_repository = AsyncMock()
    credential_repository.get_by_common_name_for_user.return_value = credential
    credential_repository.upsert.side_effect = lambda item: item

    openvpn_client = AsyncMock()
    openvpn_client.create_user.return_value = "<ca>real</ca><cert>x</cert>\nauth-user-pass"

    server_service = AsyncMock()
    server_service.get_server.return_value = _server()

    service = OpenVpnProvisioningService(
        server_service=server_service,
        subscription_repository=AsyncMock(),
        credential_repository=credential_repository,
        capacity_service=AsyncMock(),
        password_service=PasswordService(bcrypt_rounds=4),
        openvpn_client=openvpn_client,
    )

    saved, plaintext = await service.migrate_legacy_to_auth(42, "0123456789")

    openvpn_client.create_auth_user.assert_awaited_once()
    openvpn_client.create_user.assert_awaited_once()
    assert openvpn_client.create_user.await_args.kwargs["auth_mode"] == "dual"
    assert plaintext
    assert saved.auth_mode == OpenVpnAuthMode.dual
    assert saved.vpn_username == "0123456789"
    assert "auth-user-pass" in saved.ovpn_content


@pytest.mark.asyncio
async def test_finalize_auth_migration_revokes_cert_and_sets_user_pass(monkeypatch):
    monkeypatch.setenv("OPENVPN_LEGACY_MIGRATION_ENABLED", "true")
    monkeypatch.setenv("OPENVPN_LEGACY_MIGRATION_GRACE_DAYS", "0")

    credential = _credential(auth_mode=OpenVpnAuthMode.dual)
    credential.password_hash = "$2b$04$hash"
    credential.auth_synced_at = datetime.now(UTC) - timedelta(days=1)

    credential_repository = AsyncMock()
    credential_repository.get_by_common_name_for_user.return_value = credential
    credential_repository.upsert.side_effect = lambda item: item

    openvpn_client = AsyncMock()
    openvpn_client.create_user.return_value = "<ca>real</ca>\nauth-user-pass"

    server_service = AsyncMock()
    server_service.get_server.return_value = _server()

    service = OpenVpnProvisioningService(
        server_service=server_service,
        subscription_repository=AsyncMock(),
        credential_repository=credential_repository,
        capacity_service=AsyncMock(),
        password_service=PasswordService(bcrypt_rounds=4),
        openvpn_client=openvpn_client,
    )

    saved = await service.finalize_auth_migration(42, "0123456789")

    openvpn_client.delete_user.assert_awaited_once()
    openvpn_client.create_user.assert_awaited_once()
    assert openvpn_client.create_user.await_args.kwargs["auth_mode"] == "user_pass"
    assert saved.auth_mode == OpenVpnAuthMode.user_pass


@pytest.mark.asyncio
async def test_migrate_legacy_rejects_when_disabled(monkeypatch):
    monkeypatch.delenv("OPENVPN_LEGACY_MIGRATION_ENABLED", raising=False)
    monkeypatch.setenv("OPENVPN_AUTH_MODE", "dual")

    credential_repository = AsyncMock()
    credential_repository.get_by_common_name_for_user.return_value = _credential()

    service = OpenVpnProvisioningService(
        server_service=AsyncMock(),
        subscription_repository=AsyncMock(),
        credential_repository=credential_repository,
        capacity_service=AsyncMock(),
        password_service=PasswordService(bcrypt_rounds=4),
        openvpn_client=AsyncMock(),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.migrate_legacy_to_auth(42, "0123456789")
    assert exc_info.value.status_code == 400
