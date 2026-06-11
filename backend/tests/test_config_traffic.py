from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from vpn_core.bot_gateway_domain.service import BotGatewayService
from vpn_core.openvpn_sync.domain.openvpn_client_credential import (
    OpenVpnClientCredential,
    OpenVpnConfigStatus,
)
from vpn_core.openvpn_sync.services.openvpn_traffic_enforcement_service import (
    TrafficEnforcementSummary,
)
from vpn_core.subscription_domain.domain.subscription import Subscription, SubscriptionStatus


def _service(**overrides) -> BotGatewayService:
    traffic_enforcement_service = AsyncMock()
    traffic_enforcement_service.sync_and_enforce.return_value = TrafficEnforcementSummary()

    service = BotGatewayService(
        subscription_service=AsyncMock(),
        billing_service=AsyncMock(),
        commerce_service=AsyncMock(),
        openvpn_service=AsyncMock(),
        openvpn_endpoint_service=AsyncMock(),
        server_service=AsyncMock(),
        capacity_service=AsyncMock(),
        user_admin_service=AsyncMock(),
        traffic_enforcement_service=traffic_enforcement_service,
        subscription_base_url="https://example.com",
    )
    for key, value in overrides.items():
        setattr(service, f"_{key}", value)
    return service


@pytest.mark.asyncio
async def test_get_openvpn_config_traffic_syncs_live_usage_before_lookup():
    subscription = Subscription(
        id=5,
        user_id=1,
        plan_id=1,
        service_type="openvpn",
        uuid="sub-5",
        status=SubscriptionStatus.active,
        traffic_limit_bytes=1_073_741_824,
        traffic_used_bytes=1_286_693,
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
    )

    traffic_enforcement_service = AsyncMock()
    traffic_enforcement_service.sync_and_enforce.return_value = TrafficEnforcementSummary(
        subscriptions_checked=1,
        bytes_accounted=1_286_693,
    )
    openvpn_service = AsyncMock()
    openvpn_service.get_config_by_config_id.return_value = credential
    subscription_service = AsyncMock()
    subscription_service.get_subscription.return_value = subscription

    service = _service(
        traffic_enforcement_service=traffic_enforcement_service,
        openvpn_service=openvpn_service,
        subscription_service=subscription_service,
    )

    summary = await service.get_openvpn_config_traffic(1, "9149049423")

    traffic_enforcement_service.sync_and_enforce.assert_awaited_once()
    assert summary.traffic_used_bytes == 1_286_693
    assert summary.traffic_limit_bytes == 1_073_741_824
    assert summary.remaining_bytes == 1_073_741_824 - 1_286_693
