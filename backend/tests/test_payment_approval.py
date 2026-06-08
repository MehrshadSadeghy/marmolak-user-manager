from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from vpn_core.billing_domain.domain.payment_request import PaymentPurpose, PaymentRequest, PaymentRequestStatus
from vpn_core.bot_gateway_domain.service import BotGatewayService
from vpn_core.subscription_domain.domain.plan import Plan
from vpn_core.subscription_domain.domain.subscription import Subscription, SubscriptionStatus
from vpn_core.subscription_domain.domain.user import User


def _payment_request(*, purpose: PaymentPurpose, amount_toman: int = 50_000) -> PaymentRequest:
    return PaymentRequest(
        id=7,
        user_id=42,
        purpose=purpose,
        amount_toman=amount_toman,
        plan_id=1,
        status=PaymentRequestStatus.pending_approval,
        created_at=datetime.now(UTC),
    )


def _plan() -> Plan:
    return Plan(
        id=1,
        name="Test",
        service_type="openvpn",
        duration_days=30,
        traffic_limit_bytes=10 * 1024**3,
        price_toman=50_000,
        is_active=True,
    )


def _user() -> User:
    return User(id=42, telegram_id="999888777", chat_id="999888777", username="buyer")


def _subscription() -> Subscription:
    return Subscription(
        id=10,
        user_id=42,
        plan_id=1,
        service_type="openvpn",
        uuid="550e8400-e29b-41d4-a716-446655440000",
        status=SubscriptionStatus.active,
        traffic_limit_bytes=10 * 1024**3,
        expire_at=datetime.now(UTC) + timedelta(days=30),
        created_at=datetime.now(UTC),
    )


def _service(**overrides) -> BotGatewayService:
    subscription_service = AsyncMock()
    billing_service = AsyncMock()
    commerce_service = AsyncMock()
    openvpn_service = AsyncMock()
    openvpn_endpoint_service = AsyncMock()
    server_service = AsyncMock()

    service = BotGatewayService(
        subscription_service=subscription_service,
        billing_service=billing_service,
        commerce_service=commerce_service,
        openvpn_service=openvpn_service,
        openvpn_endpoint_service=openvpn_endpoint_service,
        server_service=server_service,
        subscription_base_url="https://example.com",
    )

    for key, value in overrides.items():
        setattr(service, key, value)
    return service


@pytest.mark.asyncio
async def test_approve_purchase_fulfills_without_wallet_round_trip():
    request = _payment_request(purpose=PaymentPurpose.purchase)
    plan = _plan()
    subscription = _subscription()
    user = _user()

    billing_service = AsyncMock()
    billing_service.get_payment_request.return_value = request
    billing_service.get_wallet.return_value = AsyncMock(balance_toman=0)

    subscription_service = AsyncMock()
    subscription_service.get_user.return_value = user
    subscription_service.get_plan.return_value = plan
    subscription_service.list_subscriptions.return_value = []
    subscription_service.create_subscription.return_value = subscription

    commerce_service = AsyncMock()
    commerce_service.get_service_type.return_value = AsyncMock(is_enabled=True)

    service = _service(
        _billing_service=billing_service,
        _subscription_service=subscription_service,
        _commerce_service=commerce_service,
    )
    service._find_subscription_for_payment = AsyncMock(return_value=None)
    service._try_deliver = AsyncMock(return_value=None)

    result = await service.approve_payment(7, "111222333")

    billing_service.credit_wallet.assert_not_awaited()
    billing_service.debit_wallet.assert_not_awaited()
    billing_service.review_payment_request.assert_awaited_once()
    billing_service.mark_payment_completed.assert_awaited_once()
    subscription_service.create_subscription.assert_awaited_once()
    assert result.user_telegram_id == "999888777"
    assert result.purpose == PaymentPurpose.purchase.value
    assert result.purchase is not None


@pytest.mark.asyncio
async def test_approve_topup_credits_wallet_only():
    request = _payment_request(purpose=PaymentPurpose.topup)
    user = _user()

    billing_service = AsyncMock()
    billing_service.get_payment_request.return_value = request
    billing_service.get_wallet.return_value = AsyncMock(balance_toman=50_000)

    subscription_service = AsyncMock()
    subscription_service.get_user.return_value = user

    service = _service(
        _billing_service=billing_service,
        _subscription_service=subscription_service,
    )

    result = await service.approve_payment(7, "111222333")

    billing_service.credit_wallet.assert_awaited_once()
    billing_service.debit_wallet.assert_not_awaited()
    assert result.purchase is None
    assert result.purpose == PaymentPurpose.topup.value


@pytest.mark.asyncio
async def test_approve_purchase_rejects_when_payment_below_plan_price():
    request = _payment_request(purpose=PaymentPurpose.purchase, amount_toman=40_000)
    plan = _plan()

    billing_service = AsyncMock()
    billing_service.get_payment_request.return_value = request

    subscription_service = AsyncMock()
    subscription_service.get_plan.return_value = plan

    commerce_service = AsyncMock()
    commerce_service.get_service_type.return_value = AsyncMock(is_enabled=True)

    service = _service(
        _billing_service=billing_service,
        _subscription_service=subscription_service,
        _commerce_service=commerce_service,
    )
    service._find_subscription_for_payment = AsyncMock(return_value=None)
    service._get_active_plan = AsyncMock(return_value=plan)

    with pytest.raises(HTTPException) as exc:
        await service.approve_payment(7, "111222333")

    assert exc.value.status_code == 400
    billing_service.credit_wallet.assert_not_awaited()
    billing_service.review_payment_request.assert_not_awaited()
