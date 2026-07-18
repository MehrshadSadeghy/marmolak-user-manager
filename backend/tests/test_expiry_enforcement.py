from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from vpn_core.openvpn_sync.services.subscription_expiry_enforcement_service import (
    SubscriptionExpiryEnforcementService,
)
from vpn_core.subscription_domain.domain.subscription import Subscription, SubscriptionStatus


def _subscription(*, subscription_id: int = 1, user_id: int = 42) -> Subscription:
    return Subscription(
        id=subscription_id,
        user_id=user_id,
        plan_id=2,
        service_type="openvpn",
        uuid="test-uuid",
        status=SubscriptionStatus.active,
        traffic_limit_bytes=10_737_418_240,
        traffic_used_bytes=0,
        expire_at=datetime.now(UTC) - timedelta(hours=1),
    )


@pytest.mark.asyncio
async def test_enforce_expires_subscription_and_revokes_configs():
    subscription = _subscription()
    subscription_repository = AsyncMock()
    subscription_repository.list_expired_active_subscriptions.return_value = [subscription]
    subscription_repository.update_subscription.side_effect = lambda sub: sub

    provisioning_service = AsyncMock()
    provisioning_service.deactivate.return_value = 1

    service = SubscriptionExpiryEnforcementService(
        subscription_repository=subscription_repository,
        provisioning_service=provisioning_service,
    )

    summary = await service.enforce()

    assert summary.subscriptions_checked == 1
    assert summary.subscriptions_expired == 1
    assert summary.configs_revoked == 1
    provisioning_service.deactivate.assert_awaited_once()
    updated = subscription_repository.update_subscription.await_args.args[0]
    assert updated.status == SubscriptionStatus.expired


@pytest.mark.asyncio
async def test_enforce_expires_v2ray_subscription_and_revokes_configs():
    subscription = _subscription()
    subscription.service_type = "v2ray"
    subscription_repository = AsyncMock()
    subscription_repository.list_expired_active_subscriptions.return_value = [subscription]
    subscription_repository.update_subscription.side_effect = lambda sub: sub

    openvpn_service = AsyncMock()
    v2ray_service = AsyncMock()
    v2ray_service.deactivate.return_value = 1

    service = SubscriptionExpiryEnforcementService(
        subscription_repository=subscription_repository,
        provisioning_service=openvpn_service,
        v2ray_provisioning_service=v2ray_service,
    )

    summary = await service.enforce()

    assert summary.subscriptions_checked == 1
    assert summary.subscriptions_expired == 1
    assert summary.configs_revoked == 1
    v2ray_service.deactivate.assert_awaited_once()
    openvpn_service.deactivate.assert_not_awaited()


@pytest.mark.asyncio
async def test_enforce_skips_when_no_expired_subscriptions():
    subscription_repository = AsyncMock()
    subscription_repository.list_expired_active_subscriptions.return_value = []
    provisioning_service = AsyncMock()

    service = SubscriptionExpiryEnforcementService(
        subscription_repository=subscription_repository,
        provisioning_service=provisioning_service,
    )

    summary = await service.enforce()

    assert summary.subscriptions_checked == 0
    assert summary.subscriptions_expired == 0
    provisioning_service.deactivate.assert_not_awaited()
