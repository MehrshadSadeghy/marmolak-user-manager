from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from vpn_core.subscription_domain.domain.plan import Plan
from vpn_core.subscription_domain.domain.user import User
from vpn_core.user_admin_domain.service import UserAdminService


def _plan(**overrides) -> Plan:
    defaults = {
        "id": 1,
        "name": "50GB",
        "description": "",
        "service_type": "openvpn",
        "duration_days": 30,
        "traffic_limit_bytes": 50 * 1024**3,
        "price_toman": 100_000,
        "is_active": True,
    }
    defaults.update(overrides)
    return Plan(**defaults)


def _service(**overrides) -> UserAdminService:
    service = UserAdminService(
        user_admin_repository=AsyncMock(),
        subscription_repository=AsyncMock(),
        credential_repository=AsyncMock(),
        openvpn_service=AsyncMock(),
        server_service=AsyncMock(),
    )
    for key, value in overrides.items():
        setattr(service, f"_{key}" if not key.startswith("_") else key, value)
    return service


@pytest.mark.asyncio
async def test_apply_discounted_price_without_rule():
    repo = AsyncMock()
    repo.get_discount_percent.return_value = None
    service = _service(user_admin_repository=repo)
    plan = _plan()

    price, percent = await service.apply_discounted_price(7, plan)

    assert price == 100_000
    assert percent is None


@pytest.mark.asyncio
async def test_apply_discounted_price_with_collaborator_rule():
    repo = AsyncMock()
    repo.get_discount_percent.return_value = 20
    service = _service(user_admin_repository=repo)
    plan = _plan()

    price, percent = await service.apply_discounted_price(7, plan)

    assert price == 80_000
    assert percent == 20


@pytest.mark.asyncio
async def test_assert_user_not_blocked_raises():
    subscription_repository = AsyncMock()
    subscription_repository.get_user.return_value = User(
        id=1,
        telegram_id="123",
        chat_id="123",
        is_blocked=True,
    )
    service = _service(subscription_repository=subscription_repository)

    with pytest.raises(HTTPException) as exc:
        await service.assert_user_not_blocked(1)

    assert exc.value.status_code == 403
