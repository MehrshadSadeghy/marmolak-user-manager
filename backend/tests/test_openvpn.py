from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from vpn_core.openvpn_sync.domain.commands import DeactivateOpenVpnCommand
from vpn_core.openvpn_sync.services.helpers import build_common_name, node_api_configured
from vpn_core.openvpn_sync.services.openvpn_traffic_service import OpenVpnTrafficService
from vpn_core.server_management_domain.domain.capacity import ServerCapacity
from vpn_core.server_management_domain.domain.connection_info import ConnectionInfo
from vpn_core.server_management_domain.domain.openvpn_settings import OpenVpnSettings
from vpn_core.server_management_domain.domain.server import Server
from vpn_core.subscription_domain.domain.subscription import Subscription, SubscriptionStatus


def _server(*, name: str, openvpn_enabled: bool = False, xray_tag: str | None = None) -> Server:
    return Server(
        name=name,
        country_code="US",
        cpu_cores=2,
        ram_mb=2048,
        disk_gb=40,
        connection=ConnectionInfo(host="10.0.0.1", api_port=8090),
        capacity=ServerCapacity(max_bandwidth_mbps=1000),
        xray_inbound_tag=xray_tag,
        openvpn=OpenVpnSettings(
            enabled=openvpn_enabled,
            node_api_secret="secret" if openvpn_enabled else None,
            vpn_host="ovpn.example.com",
        ),
    )


def test_build_common_name_default_slot():
    assert build_common_name("123456789") == "tg-123456789"


def test_build_common_name_with_slot_index():
    assert build_common_name("123456789", 2) == "tg-123456789-2"


def test_build_common_name_slot_zero_is_base():
    assert build_common_name("99", 0) == "tg-99"


@pytest.mark.asyncio
async def test_openvpn_traffic_service_enforces_bandwidth_limit():
    subscription = Subscription(
        id=1,
        user_id=42,
        plan_id=1,
        uuid="550e8400-e29b-41d4-a716-446655440000",
        status=SubscriptionStatus.active,
        traffic_limit_bytes=1_000,
        expire_at=datetime.now(UTC) + timedelta(days=30),
    )

    subscription_repository = AsyncMock()
    subscription_repository.get_subscription.return_value = subscription
    subscription_repository.update_subscription.return_value = subscription

    traffic_repository = AsyncMock()
    traffic_repository.total_bytes_for_user.return_value = 1_000

    provisioning_service = AsyncMock()
    provisioning_service.deactivate.return_value = 1

    service = OpenVpnTrafficService(
        traffic_repository=traffic_repository,
        subscription_repository=subscription_repository,
        provisioning_service=provisioning_service,
    )

    await service._enforce_subscription_quota(subscription.id)

    assert subscription.status == SubscriptionStatus.traffic_exceeded
    subscription_repository.update_subscription.assert_awaited_once_with(subscription)
    provisioning_service.deactivate.assert_awaited_once_with(
        DeactivateOpenVpnCommand(user_id=42, reason="bandwidth_limit")
    )


def test_server_capability_checks():
    v2ray_only = _server(name="V2", xray_tag="inbound-vless")
    openvpn_only = _server(name="openvpn_only", openvpn_enabled=True)

    assert node_api_configured(v2ray_only) is False
    assert bool(v2ray_only.xray_inbound_tag) is True

    assert node_api_configured(openvpn_only) is True
    assert bool(openvpn_only.xray_inbound_tag) is False
