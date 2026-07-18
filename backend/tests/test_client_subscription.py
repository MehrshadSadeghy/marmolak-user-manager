import base64
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from vpn_core.client_subscription_domain.service import (
    ClientSubscriptionConfig,
    ClientSubscriptionService,
)
from vpn_core.subscription_domain.domain.subscription import Subscription, SubscriptionStatus
from vpn_core.subscription_domain.domain.user import User
from vpn_core.v2ray_sync.domain.v2ray_client_credential import (
    V2RayClientCredential,
    V2RayConfigStatus,
)


def _service(**overrides) -> ClientSubscriptionService:
    subscription_service = AsyncMock()
    v2ray_service = AsyncMock()
    service = ClientSubscriptionService(
        subscription_service=subscription_service,
        v2ray_service=v2ray_service,
        config=ClientSubscriptionConfig(base_url="https://vpn.example.com"),
    )
    for key, value in overrides.items():
        setattr(service, f"_{key}", value)
    return service


@pytest.mark.asyncio
async def test_get_subscription_url_for_user():
    user = User(id=1, telegram_id="123", chat_id="123", subscription_token="abc123")
    subscription_service = AsyncMock()
    subscription_service.get_user.return_value = user
    subscription_service.ensure_subscription_token.return_value = user
    service = _service(subscription_service=subscription_service)

    url = await service.get_subscription_url_for_user(1)

    assert url == "https://vpn.example.com/sub/abc123"


@pytest.mark.asyncio
async def test_render_subscription_feed_returns_base64_links():
    now = datetime.now(UTC)
    user = User(id=1, telegram_id="123", chat_id="123", subscription_token="abc123")
    subscription = Subscription(
        id=10,
        user_id=1,
        plan_id=1,
        service_type="v2ray",
        uuid="test-uuid",
        status=SubscriptionStatus.active,
        expire_at=now + timedelta(days=7),
        traffic_limit_bytes=10_000,
        traffic_used_bytes=1_000,
    )
    credential = V2RayClientCredential(
        user_id=1,
        subscription_id=10,
        server_id=1,
        telegram_id="123",
        email="1234567890",
        client_uuid="11111111-2222-3333-4444-555555555555",
        slot_index=0,
        vless_link="vless://11111111-2222-3333-4444-555555555555@vpn.example.com:443?type=ws&security=none",
        status=V2RayConfigStatus.active,
    )

    subscription_service = AsyncMock()
    subscription_service.get_user.return_value = user
    subscription_service.list_subscriptions.return_value = [subscription]
    v2ray_service = AsyncMock()
    v2ray_service.list_configs.return_value = [credential]
    service = _service(
        subscription_service=subscription_service,
        v2ray_service=v2ray_service,
    )

    feed = await service.render_subscription_feed("abc123")
    decoded = base64.b64decode(feed.body.encode("ascii")).decode("utf-8")

    assert decoded == credential.vless_link
    assert feed.link_count == 1
    assert "subscription-userinfo" in feed.headers


@pytest.mark.asyncio
async def test_render_subscription_feed_not_found_for_unknown_token():
    subscription_service = AsyncMock()
    subscription_service.get_user.return_value = None
    service = _service(subscription_service=subscription_service)

    with pytest.raises(HTTPException) as exc:
        await service.render_subscription_feed("missing-token")

    assert exc.value.status_code == 404
