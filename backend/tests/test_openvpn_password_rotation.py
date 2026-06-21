from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from vpn_core.openvpn_sync.domain.auth_mode import OpenVpnAuthMode
from vpn_core.openvpn_sync.domain.openvpn_client_credential import (
    OpenVpnClientCredential,
    OpenVpnConfigStatus,
)
from vpn_core.openvpn_sync.services.openvpn_provisioning_service import OpenVpnProvisioningService
from vpn_core.openvpn_sync.services.password_service import PasswordService
from vpn_core.server_management_domain.domain.capacity import ServerCapacity
from vpn_core.server_management_domain.domain.connection_info import ConnectionInfo
from vpn_core.server_management_domain.domain.openvpn_settings import OpenVpnSettings
from vpn_core.server_management_domain.domain.server import Server


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


def _credential(*, auth_mode: OpenVpnAuthMode) -> OpenVpnClientCredential:
    return OpenVpnClientCredential(
        id=1,
        user_id=42,
        subscription_id=7,
        server_id=1,
        telegram_id="123",
        common_name="0123456789",
        ovpn_content="<ca>x</ca>",
        auth_mode=auth_mode,
        vpn_username="0123456789",
        status=OpenVpnConfigStatus.active,
    )


@pytest.mark.asyncio
async def test_rotate_password_updates_hash_and_returns_plaintext_once():
    credential = _credential(auth_mode=OpenVpnAuthMode.dual)
    credential_repository = AsyncMock()
    credential_repository.get_by_common_name_for_user.return_value = credential
    credential_repository.upsert.side_effect = lambda item: item

    server_service = AsyncMock()
    server_service.get_server.return_value = _server()

    openvpn_client = AsyncMock()
    service = OpenVpnProvisioningService(
        server_service=server_service,
        subscription_repository=AsyncMock(),
        credential_repository=credential_repository,
        capacity_service=AsyncMock(),
        password_service=PasswordService(bcrypt_rounds=4),
        openvpn_client=openvpn_client,
    )

    saved, plaintext = await service.rotate_password(42, "0123456789")

    openvpn_client.rotate_auth_user.assert_awaited_once()
    assert plaintext
    assert saved.password_hash
    assert PasswordService(bcrypt_rounds=4).verify_password(plaintext, saved.password_hash)
    assert saved.password_rotated_at is not None


@pytest.mark.asyncio
async def test_rotate_password_rejects_certificate_mode():
    credential_repository = AsyncMock()
    credential_repository.get_by_common_name_for_user.return_value = _credential(
        auth_mode=OpenVpnAuthMode.certificate
    )

    service = OpenVpnProvisioningService(
        server_service=AsyncMock(),
        subscription_repository=AsyncMock(),
        credential_repository=credential_repository,
        capacity_service=AsyncMock(),
        password_service=PasswordService(bcrypt_rounds=4),
        openvpn_client=AsyncMock(),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.rotate_password(42, "0123456789")
    assert exc_info.value.status_code == 400
