from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from vpn_core.billing_domain.domain.payment_request import PaymentPurpose, PaymentRequest, PaymentRequestStatus
from vpn_core.bot_gateway_domain.service import BotGatewayService
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


def _user() -> User:
    return User(id=42, telegram_id="999888777", chat_id="999888777", username="buyer")


def _service(**overrides) -> BotGatewayService:
    subscription_service = AsyncMock()
    billing_service = AsyncMock()
    commerce_service = AsyncMock()
    openvpn_service = AsyncMock()
    openvpn_endpoint_service = AsyncMock()
    server_service = AsyncMock()
    user_admin_service = AsyncMock()
    user_admin_service.is_user_blocked.return_value = False

    async def _apply_discount(user_id, plan):
        return plan.price_toman, None

    user_admin_service.assert_user_not_blocked = AsyncMock()
    user_admin_service.apply_discounted_price = AsyncMock(side_effect=_apply_discount)

    service = BotGatewayService(
        subscription_service=subscription_service,
        billing_service=billing_service,
        commerce_service=commerce_service,
        openvpn_service=openvpn_service,
        openvpn_endpoint_service=openvpn_endpoint_service,
        server_service=server_service,
        user_admin_service=user_admin_service,
        subscription_base_url="https://example.com",
    )

    for key, value in overrides.items():
        setattr(service, key, value)
    return service


@pytest.mark.asyncio
async def test_approve_purchase_only_credits_wallet():
    request = _payment_request(purpose=PaymentPurpose.purchase)
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
    billing_service.review_payment_request.assert_awaited_once()
    billing_service.mark_payment_completed.assert_awaited_once()
    subscription_service.create_subscription.assert_not_called()
    assert result.purchase is None
    assert result.purpose == PaymentPurpose.purchase.value


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
async def test_approve_renewal_only_credits_wallet():
    request = _payment_request(purpose=PaymentPurpose.renewal)
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
    subscription_service.renew_subscription.assert_not_called()
    assert result.purchase is None
