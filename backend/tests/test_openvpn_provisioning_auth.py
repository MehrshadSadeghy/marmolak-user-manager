from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from vpn_core.openvpn_sync.domain.auth_mode import OpenVpnAuthMode
from vpn_core.openvpn_sync.domain.commands import ProvisionOpenVpnCommand
from vpn_core.openvpn_sync.domain.openvpn_client_credential import OpenVpnConfigStatus
from vpn_core.openvpn_sync.services.openvpn_provisioning_service import OpenVpnProvisioningService
from vpn_core.openvpn_sync.services.password_service import PasswordService
from vpn_core.server_management_domain.domain.capacity import ServerCapacity
from vpn_core.server_management_domain.domain.connection_info import ConnectionInfo
from vpn_core.server_management_domain.domain.openvpn_settings import OpenVpnSettings
from vpn_core.server_management_domain.domain.server import Server
from vpn_core.subscription_domain.domain.subscription import Subscription, SubscriptionStatus
from vpn_core.subscription_domain.domain.user import User


class _CapacityServiceStub:
    async def assert_server_has_capacity(self, server_id: int) -> None:
        return None

    async def sync_current_users(self, server_id: int) -> None:
        return None


def _openvpn_server(*, server_id: int = 1) -> Server:
    return Server(
        id=server_id,
        name="openvpn-1",
        country_code="DE",
        cpu_cores=2,
        ram_mb=2048,
        disk_gb=40,
        connection=ConnectionInfo(host="10.0.0.1", api_port=8090),
        capacity=ServerCapacity(max_bandwidth_mbps=1000, max_users=100),
        openvpn=OpenVpnSettings(
            enabled=True,
            node_api_secret="node-secret",
            vpn_host="vpn.example.com",
        ),
    )


def _subscription(*, user_id: int = 42, subscription_id: int = 7) -> Subscription:
    return Subscription(
        id=subscription_id,
        user_id=user_id,
        plan_id=1,
        service_type="openvpn",
        uuid="550e8400-e29b-41d4-a716-446655440000",
        status=SubscriptionStatus.active,
        traffic_limit_bytes=10_000_000_000,
        expire_at=datetime.now(UTC) + timedelta(days=30),
    )


def _build_service(
    *,
    openvpn_client: AsyncMock,
    credential_repository: AsyncMock | None = None,
) -> OpenVpnProvisioningService:
    server = _openvpn_server()
    subscription = _subscription()

    subscription_repository = AsyncMock()
    subscription_repository.get_user.return_value = User(
        id=42,
        telegram_id="123456789",
        chat_id="123456789",
        username="tester",
    )
    subscription_repository.get_subscription.return_value = subscription

    credential_repository = credential_repository or AsyncMock()
    credential_repository.list_by_user.return_value = []
    credential_repository.get_by_common_name.return_value = None
    credential_repository.upsert.side_effect = lambda credential: credential

    server_service = AsyncMock()
    server_service.get_server.return_value = server

    capacity_service = _CapacityServiceStub()

    return OpenVpnProvisioningService(
        server_service=server_service,
        subscription_repository=subscription_repository,
        credential_repository=credential_repository,
        capacity_service=capacity_service,
        password_service=PasswordService(bcrypt_rounds=4),
        openvpn_client=openvpn_client,
    )


@pytest.mark.asyncio
async def test_provision_certificate_mode_skips_auth_sync(monkeypatch):
    monkeypatch.setenv("OPENVPN_AUTH_MODE", "certificate")
    openvpn_client = AsyncMock()
    openvpn_client.create_user.return_value = "<ca>real</ca><cert>client</cert>"

    service = _build_service(openvpn_client=openvpn_client)
    result = await service.provision(
        ProvisionOpenVpnCommand(user_id=42, server_id=1, subscription_id=7)
    )

    openvpn_client.create_auth_user.assert_not_called()
    assert result.ephemeral_passwords == {}
    credential = result.credentials[0]
    assert credential.auth_mode == OpenVpnAuthMode.certificate
    assert credential.password_hash is None
    assert credential.vpn_username is None


@pytest.mark.asyncio
async def test_provision_dual_mode_syncs_auth_and_returns_ephemeral_password(monkeypatch):
    monkeypatch.setenv("OPENVPN_AUTH_MODE", "dual")
    monkeypatch.setenv("OPENVPN_PROVISIONING_AUTH_MODE", "dual")
    openvpn_client = AsyncMock()
    openvpn_client.create_auth_user.return_value = {"status": "success", "created": True}
    openvpn_client.create_user.return_value = "<ca>real</ca><cert>client</cert>"

    credential_repository = AsyncMock()
    credential_repository.list_by_user = AsyncMock(return_value=[])
    credential_repository.get_by_common_name = AsyncMock(return_value=None)
    credential_repository.upsert = AsyncMock(side_effect=lambda credential: credential)

    service = _build_service(
        openvpn_client=openvpn_client,
        credential_repository=credential_repository,
    )
    result = await service.provision(
        ProvisionOpenVpnCommand(user_id=42, server_id=1, subscription_id=7)
    )

    config_id = result.credentials[0].common_name
    stored = result.credentials[0]
    openvpn_client.create_auth_user.assert_awaited_once()
    auth_args = openvpn_client.create_auth_user.await_args
    assert auth_args.args[1] == config_id
    assert auth_args.args[2].startswith("$2")

    assert config_id in result.ephemeral_passwords
    plaintext = result.ephemeral_passwords[config_id]
    assert PasswordService(bcrypt_rounds=4).verify_password(
        plaintext,
        stored.password_hash,
    )

    assert stored.auth_mode == OpenVpnAuthMode.dual
    assert stored.vpn_username == config_id
    assert stored.auth_synced_at is not None
    assert stored.status == OpenVpnConfigStatus.active


@pytest.mark.asyncio
async def test_provision_user_pass_mode_syncs_auth_without_client_cert(monkeypatch):
    monkeypatch.setenv("OPENVPN_AUTH_MODE", "user_pass")
    openvpn_client = AsyncMock()
    openvpn_client.create_auth_user.return_value = {"status": "success", "created": True}
    openvpn_client.create_user.return_value = "<ca>real</ca>\nauth-user-pass"

    service = _build_service(openvpn_client=openvpn_client)
    result = await service.provision(
        ProvisionOpenVpnCommand(user_id=42, server_id=1, subscription_id=7)
    )

    openvpn_client.create_auth_user.assert_awaited_once()
    assert result.credentials[0].auth_mode == OpenVpnAuthMode.user_pass
    assert result.ephemeral_passwords
    assert "auth-user-pass" in result.credentials[0].ovpn_content
    assert "<cert>" not in result.credentials[0].ovpn_content


@pytest.mark.asyncio
async def test_provision_user_pass_rolls_back_auth_only_when_profile_build_fails(monkeypatch):
    monkeypatch.setenv("OPENVPN_AUTH_MODE", "user_pass")
    openvpn_client = AsyncMock()
    openvpn_client.create_auth_user.return_value = {"status": "success", "created": True}
    openvpn_client.create_user.side_effect = RuntimeError("profile build failed")

    service = _build_service(openvpn_client=openvpn_client)

    with pytest.raises(HTTPException) as exc_info:
        await service.provision(
            ProvisionOpenVpnCommand(user_id=42, server_id=1, subscription_id=7)
        )
    assert exc_info.value.status_code == 502

    openvpn_client.delete_auth_user.assert_awaited_once()
    openvpn_client.delete_user.assert_not_called()


@pytest.mark.asyncio
async def test_provision_rolls_back_auth_user_when_cert_creation_fails(monkeypatch):
    monkeypatch.setenv("OPENVPN_AUTH_MODE", "dual")
    monkeypatch.setenv("OPENVPN_PROVISIONING_AUTH_MODE", "dual")
    openvpn_client = AsyncMock()
    openvpn_client.create_auth_user.return_value = {"status": "success", "created": True}
    openvpn_client.create_user.side_effect = RuntimeError("cert failed")

    service = _build_service(openvpn_client=openvpn_client)

    with pytest.raises(HTTPException) as exc_info:
        await service.provision(
            ProvisionOpenVpnCommand(user_id=42, server_id=1, subscription_id=7)
        )
    assert exc_info.value.status_code == 502

    openvpn_client.delete_auth_user.assert_awaited_once()
    openvpn_client.delete_user.assert_not_called()


@pytest.mark.asyncio
async def test_provision_dual_mode_applies_server_auth_when_enabled(monkeypatch):
    monkeypatch.setenv("OPENVPN_AUTH_MODE", "dual")
    monkeypatch.setenv("OPENVPN_AUTO_APPLY_SERVER_AUTH", "true")
    openvpn_client = AsyncMock()
    openvpn_client.create_auth_user.return_value = {"status": "success", "created": True}
    openvpn_client.create_user.return_value = "<ca>real</ca><cert>client</cert>"
    openvpn_client.apply_auth_mode.return_value = {"status": "success", "auth_mode": "dual"}

    service = _build_service(openvpn_client=openvpn_client)
    await service.provision(
        ProvisionOpenVpnCommand(user_id=42, server_id=1, subscription_id=7)
    )

    openvpn_client.apply_auth_mode.assert_awaited_once()
    assert openvpn_client.apply_auth_mode.await_args.args[1] == "dual"


@pytest.mark.asyncio
async def test_provision_dual_mode_skips_server_auth_apply_by_default(monkeypatch):
    monkeypatch.setenv("OPENVPN_AUTH_MODE", "dual")
    monkeypatch.delenv("OPENVPN_AUTO_APPLY_SERVER_AUTH", raising=False)
    openvpn_client = AsyncMock()
    openvpn_client.create_auth_user.return_value = {"status": "success", "created": True}
    openvpn_client.create_user.return_value = "<ca>real</ca><cert>client</cert>"

    service = _build_service(openvpn_client=openvpn_client)
    await service.provision(
        ProvisionOpenVpnCommand(user_id=42, server_id=1, subscription_id=7)
    )

    openvpn_client.apply_auth_mode.assert_not_called()


@pytest.mark.asyncio
async def test_phase6_rollout_dual_server_provisions_user_pass_credentials(monkeypatch):
    monkeypatch.setenv("OPENVPN_AUTH_MODE", "dual")
    monkeypatch.delenv("OPENVPN_PROVISIONING_AUTH_MODE", raising=False)
    openvpn_client = AsyncMock()
    openvpn_client.create_auth_user.return_value = {"status": "success", "created": True}
    openvpn_client.create_user.return_value = "<ca>real</ca><cert>client</cert>"

    service = _build_service(openvpn_client=openvpn_client)
    result = await service.provision(
        ProvisionOpenVpnCommand(user_id=42, server_id=1, subscription_id=7)
    )

    credential = result.credentials[0]
    assert credential.auth_mode == OpenVpnAuthMode.user_pass
    assert credential.vpn_username == credential.common_name
    assert result.ephemeral_passwords
    create_user_kwargs = openvpn_client.create_user.await_args.kwargs
    assert create_user_kwargs["auth_mode"] == "user_pass"


@pytest.mark.asyncio
async def test_provision_rolls_back_cert_when_auth_sync_fails(monkeypatch):
    monkeypatch.setenv("OPENVPN_AUTH_MODE", "dual")
    monkeypatch.setenv("OPENVPN_PROVISIONING_AUTH_MODE", "dual")
    openvpn_client = AsyncMock()
    openvpn_client.create_auth_user.side_effect = RuntimeError("auth sync failed")

    service = _build_service(openvpn_client=openvpn_client)

    with pytest.raises(HTTPException) as exc_info:
        await service.provision(
            ProvisionOpenVpnCommand(user_id=42, server_id=1, subscription_id=7)
        )
    assert exc_info.value.status_code == 502

    openvpn_client.create_user.assert_not_called()
    openvpn_client.delete_auth_user.assert_not_called()
    openvpn_client.delete_user.assert_not_called()
