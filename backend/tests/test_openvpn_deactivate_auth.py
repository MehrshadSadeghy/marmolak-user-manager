from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from vpn_core.openvpn_sync.domain.auth_mode import OpenVpnAuthMode
from vpn_core.openvpn_sync.domain.commands import DeactivateOpenVpnCommand
from vpn_core.openvpn_sync.domain.openvpn_client_credential import (
    OpenVpnClientCredential,
    OpenVpnConfigStatus,
)
from vpn_core.openvpn_sync.domain.traffic_snapshot import OpenVpnTrafficSnapshot
from vpn_core.openvpn_sync.services.openvpn_provisioning_service import OpenVpnProvisioningService
from vpn_core.openvpn_sync.services.openvpn_traffic_enforcement_service import (
    OpenVpnTrafficEnforcementService,
)
from vpn_core.openvpn_sync.services.subscription_expiry_enforcement_service import (
    SubscriptionExpiryEnforcementService,
)
from vpn_core.server_management_domain.domain.capacity import ServerCapacity
from vpn_core.server_management_domain.domain.connection_info import ConnectionInfo
from vpn_core.server_management_domain.domain.openvpn_settings import OpenVpnSettings
from vpn_core.server_management_domain.domain.server import Server, ServerStatus
from vpn_core.subscription_domain.domain.subscription import Subscription, SubscriptionStatus


def _server(*, server_id: int = 1) -> Server:
    return Server(
        id=server_id,
        name="node-1",
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
        status=ServerStatus.online,
        is_active=True,
    )


def _credential(
    *,
    credential_id: int = 1,
    auth_mode: OpenVpnAuthMode = OpenVpnAuthMode.certificate,
) -> OpenVpnClientCredential:
    return OpenVpnClientCredential(
        id=credential_id,
        user_id=42,
        subscription_id=7,
        server_id=1,
        telegram_id="123456789",
        common_name="0123456789",
        ovpn_content="<ca>x</ca>",
        auth_mode=auth_mode,
        vpn_username="0123456789" if auth_mode != OpenVpnAuthMode.certificate else None,
        status=OpenVpnConfigStatus.active,
    )


def _build_provisioning_service(
    *,
    openvpn_client: AsyncMock,
    credential_repository: AsyncMock,
) -> OpenVpnProvisioningService:
    server_service = AsyncMock()
    server_service.get_server.return_value = _server()

    capacity_service = AsyncMock()
    credential_repository.revoke.return_value = _credential()

    return OpenVpnProvisioningService(
        server_service=server_service,
        subscription_repository=AsyncMock(),
        credential_repository=credential_repository,
        capacity_service=capacity_service,
        openvpn_client=openvpn_client,
    )


@pytest.mark.asyncio
async def test_deactivate_certificate_mode_deletes_cert_only():
    credential = _credential(auth_mode=OpenVpnAuthMode.certificate)
    credential_repository = AsyncMock()
    credential_repository.list_by_user.return_value = [credential]
    openvpn_client = AsyncMock()

    service = _build_provisioning_service(
        openvpn_client=openvpn_client,
        credential_repository=credential_repository,
    )

    revoked = await service.deactivate(
        DeactivateOpenVpnCommand(user_id=42, subscription_id=7, reason="manual")
    )

    assert revoked == 1
    openvpn_client.delete_user.assert_awaited_once()
    openvpn_client.delete_auth_user.assert_not_called()


@pytest.mark.asyncio
async def test_deactivate_dual_mode_deletes_auth_and_cert():
    credential = _credential(auth_mode=OpenVpnAuthMode.dual)
    credential_repository = AsyncMock()
    credential_repository.list_by_user.return_value = [credential]
    openvpn_client = AsyncMock()

    service = _build_provisioning_service(
        openvpn_client=openvpn_client,
        credential_repository=credential_repository,
    )

    revoked = await service.deactivate(
        DeactivateOpenVpnCommand(user_id=42, subscription_id=7, reason="subscription_expired")
    )

    assert revoked == 1
    openvpn_client.delete_auth_user.assert_awaited_once()
    assert openvpn_client.delete_auth_user.await_args.args[1] == "0123456789"
    openvpn_client.delete_user.assert_awaited_once()


@pytest.mark.asyncio
async def test_deactivate_user_pass_mode_deletes_auth_only():
    credential = _credential(auth_mode=OpenVpnAuthMode.user_pass)
    credential_repository = AsyncMock()
    credential_repository.list_by_user.return_value = [credential]
    openvpn_client = AsyncMock()

    service = _build_provisioning_service(
        openvpn_client=openvpn_client,
        credential_repository=credential_repository,
    )

    revoked = await service.deactivate(
        DeactivateOpenVpnCommand(user_id=42, subscription_id=7, reason="bandwidth_limit")
    )

    assert revoked == 1
    openvpn_client.delete_auth_user.assert_awaited_once()
    openvpn_client.delete_user.assert_not_called()


@pytest.mark.asyncio
async def test_expiry_enforcement_revokes_dual_auth_via_deactivate():
    subscription = Subscription(
        id=7,
        user_id=42,
        plan_id=1,
        service_type="openvpn",
        uuid="sub-7",
        status=SubscriptionStatus.active,
        traffic_limit_bytes=10_000_000_000,
        expire_at=datetime.now(UTC) - timedelta(hours=1),
    )
    subscription_repository = AsyncMock()
    subscription_repository.list_expired_active_subscriptions.return_value = [subscription]
    subscription_repository.update_subscription.side_effect = lambda sub: sub

    credential = _credential(auth_mode=OpenVpnAuthMode.dual)
    credential_repository = AsyncMock()
    credential_repository.list_by_user.return_value = [credential]
    credential_repository.revoke.return_value = credential

    openvpn_client = AsyncMock()
    provisioning_service = _build_provisioning_service(
        openvpn_client=openvpn_client,
        credential_repository=credential_repository,
    )

    expiry_service = SubscriptionExpiryEnforcementService(
        subscription_repository=subscription_repository,
        provisioning_service=provisioning_service,
    )

    summary = await expiry_service.enforce()

    assert summary.subscriptions_expired == 1
    assert summary.configs_revoked == 1
    openvpn_client.delete_auth_user.assert_awaited_once()
    openvpn_client.delete_user.assert_awaited_once()


@pytest.mark.asyncio
async def test_traffic_enforcement_quota_revokes_dual_auth_via_deactivate():
    subscription = Subscription(
        id=7,
        user_id=42,
        plan_id=1,
        service_type="openvpn",
        uuid="sub-7",
        status=SubscriptionStatus.active,
        traffic_limit_bytes=1_000,
        traffic_used_bytes=0,
        expire_at=datetime.now(UTC) + timedelta(days=30),
    )
    credential = _credential(auth_mode=OpenVpnAuthMode.dual)
    credential.last_status_bytes = 0

    subscription_repository = AsyncMock()
    subscription_repository.get_subscription.return_value = subscription
    subscription_repository.update_subscription.side_effect = lambda sub: sub

    credential_repository = AsyncMock()
    credential_repository.list_active_with_subscription.return_value = [credential]
    credential_repository.list_by_user.return_value = [credential]
    credential_repository.revoke.return_value = credential

    openvpn_client = AsyncMock()
    openvpn_client.fetch_client_traffic.return_value = OpenVpnTrafficSnapshot(
        live={"0123456789": 1_500}
    )
    openvpn_client.consume_disconnect_traffic = AsyncMock()

    provisioning_service = _build_provisioning_service(
        openvpn_client=openvpn_client,
        credential_repository=credential_repository,
    )

    server_service = AsyncMock()
    server_service.list_servers.return_value = [_server()]

    traffic_service = OpenVpnTrafficEnforcementService(
        subscription_repository=subscription_repository,
        credential_repository=credential_repository,
        provisioning_service=provisioning_service,
        server_service=server_service,
        openvpn_client=openvpn_client,
    )

    summary = await traffic_service.sync_and_enforce()

    assert summary.subscriptions_exceeded == 1
    assert summary.configs_revoked == 1
    openvpn_client.delete_auth_user.assert_awaited_once()
    openvpn_client.delete_user.assert_awaited_once()
    assert subscription.status == SubscriptionStatus.traffic_exceeded
