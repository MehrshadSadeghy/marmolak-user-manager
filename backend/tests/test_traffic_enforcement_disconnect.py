from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from vpn_core.openvpn_sync.domain.openvpn_client_credential import (
    OpenVpnClientCredential,
    OpenVpnConfigStatus,
)
from vpn_core.openvpn_sync.domain.traffic_snapshot import OpenVpnTrafficSnapshot
from vpn_core.openvpn_sync.services.openvpn_traffic_enforcement_service import (
    OpenVpnTrafficEnforcementService,
)
from vpn_core.server_management_domain.domain.capacity import ServerCapacity
from vpn_core.server_management_domain.domain.connection_info import ConnectionInfo
from vpn_core.server_management_domain.domain.openvpn_settings import OpenVpnSettings
from vpn_core.server_management_domain.domain.server import Server, ServerStatus
from vpn_core.subscription_domain.domain.subscription import Subscription, SubscriptionStatus


def _server() -> Server:
    return Server(
        id=1,
        name="node",
        country_code="DE",
        cpu_cores=2,
        ram_mb=4096,
        disk_gb=40,
        connection=ConnectionInfo(host="144.31.167.163", api_port=8090),
        capacity=ServerCapacity(max_bandwidth_mbps=1000),
        openvpn=OpenVpnSettings(
            enabled=True,
            node_api_secret="secret",
            vpn_host="144.31.167.163",
            vpn_port=1433,
            vpn_proto="udp",
        ),
        status=ServerStatus.online,
        is_active=True,
    )


@pytest.mark.asyncio
async def test_disconnect_pending_accounts_tail_and_resets_last_status():
    subscription = Subscription(
        id=5,
        user_id=1,
        plan_id=1,
        service_type="openvpn",
        uuid="sub-5",
        status=SubscriptionStatus.active,
        traffic_limit_bytes=10_000_000_000,
        traffic_used_bytes=100_000_000,
        expire_at=datetime.now(UTC) + timedelta(days=30),
    )
    credential = OpenVpnClientCredential(
        id=6,
        user_id=1,
        subscription_id=5,
        server_id=1,
        telegram_id="8322619451",
        common_name="9149049423",
        ovpn_content="client",
        status=OpenVpnConfigStatus.active,
        last_status_bytes=100_000_000,
    )

    subscription_repository = AsyncMock()
    subscription_repository.get_subscription.return_value = subscription
    subscription_repository.update_subscription.side_effect = lambda sub: sub

    credential_repository = AsyncMock()
    credential_repository.list_active_with_subscription.return_value = [credential]

    openvpn_client = AsyncMock()
    openvpn_client.fetch_client_traffic.return_value = OpenVpnTrafficSnapshot(
        live={},
        disconnect={"9149049423": 600_000_000},
    )

    service = OpenVpnTrafficEnforcementService(
        subscription_repository=subscription_repository,
        credential_repository=credential_repository,
        provisioning_service=AsyncMock(),
        server_service=AsyncMock(list_servers=AsyncMock(return_value=[_server()])),
        openvpn_client=openvpn_client,
    )

    summary = await service.sync_and_enforce()

    assert summary.bytes_accounted == 500_000_000
    assert summary.disconnect_events_accounted == 1
    assert subscription.traffic_used_bytes == 600_000_000
    credential_repository.update_last_status_bytes.assert_awaited_once_with(6, 0)
    openvpn_client.consume_disconnect_traffic.assert_awaited_once_with(
        _server(),
        ["9149049423"],
    )


@pytest.mark.asyncio
async def test_offline_client_does_not_reset_last_status_bytes():
    subscription = Subscription(
        id=5,
        user_id=1,
        plan_id=1,
        service_type="openvpn",
        uuid="sub-5",
        status=SubscriptionStatus.active,
        traffic_limit_bytes=10_000_000_000,
        traffic_used_bytes=100_000_000,
        expire_at=datetime.now(UTC) + timedelta(days=30),
    )
    credential = OpenVpnClientCredential(
        id=6,
        user_id=1,
        subscription_id=5,
        server_id=1,
        telegram_id="8322619451",
        common_name="9149049423",
        ovpn_content="client",
        status=OpenVpnConfigStatus.active,
        last_status_bytes=100_000_000,
    )

    subscription_repository = AsyncMock()
    subscription_repository.get_subscription.return_value = subscription

    credential_repository = AsyncMock()
    credential_repository.list_active_with_subscription.return_value = [credential]

    openvpn_client = AsyncMock()
    openvpn_client.fetch_client_traffic.return_value = OpenVpnTrafficSnapshot(live={})

    service = OpenVpnTrafficEnforcementService(
        subscription_repository=subscription_repository,
        credential_repository=credential_repository,
        provisioning_service=AsyncMock(),
        server_service=AsyncMock(list_servers=AsyncMock(return_value=[_server()])),
        openvpn_client=openvpn_client,
    )

    summary = await service.sync_and_enforce()

    assert summary.bytes_accounted == 0
    credential_repository.update_last_status_bytes.assert_not_awaited()
    openvpn_client.consume_disconnect_traffic.assert_not_awaited()
