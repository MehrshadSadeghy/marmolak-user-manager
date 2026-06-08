import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException

LOGGER = logging.getLogger(__name__)

from vpn_core.billing_domain.domain.commands import (
    CreatePaymentRequestCommand,
    CreditWalletCommand,
    DebitWalletCommand,
    ReviewPaymentRequestCommand,
    SubmitPaymentReceiptCommand,
)
from vpn_core.billing_domain.domain.payment_request import PaymentPurpose, PaymentRequestStatus
from vpn_core.billing_domain.domain.queries import ListPaymentRequestsQuery
from vpn_core.billing_domain.service import BillingService
from vpn_core.commerce_domain.service import CommerceService
from vpn_core.openvpn_sync.domain.commands import ProvisionOpenVpnCommand
from vpn_core.openvpn_sync.domain.openvpn_client_credential import OpenVpnConfigStatus
from vpn_core.openvpn_sync.services.openvpn_endpoint_service import OpenVpnEndpointService
from vpn_core.openvpn_sync.services.openvpn_provisioning_service import OpenVpnProvisioningService
from vpn_core.server_management_domain.domain.queries import ListServersQuery
from vpn_core.server_management_domain.service import ServerService
from vpn_core.subscription_domain.domain.commands import (
    CreateSubscriptionCommand,
    RenewSubscriptionCommand,
)
from vpn_core.subscription_domain.domain.plan import Plan
from vpn_core.subscription_domain.domain.queries import (
    GetPlanQuery,
    GetSubscriptionQuery,
    GetUserQuery,
    ListPlansQuery,
    ListSubscriptionsQuery,
)
from vpn_core.subscription_domain.domain.subscription import Subscription, SubscriptionStatus
from vpn_core.subscription_domain.domain.user import User
from vpn_core.subscription_domain.service import SubscriptionService


@dataclass
class ServiceConfigDelivery:
    service_type: str
    subscription_id: int
    delivery_type: str
    content: str
    filename: str | None = None


@dataclass
class UserServiceSummary:
    subscription: Subscription
    plan: Plan | None
    is_active: bool
    remaining_days: int
    remaining_bytes: int
    status_label: str


@dataclass
class PurchasePreview:
    plan: Plan
    wallet_balance_toman: int
    price_toman: int
    sufficient_balance: bool
    shortfall_toman: int


@dataclass
class PurchaseResult:
    subscription: Subscription
    wallet_balance_toman: int
    paid_from_wallet: bool
    payment_request_id: int | None
    delivery: ServiceConfigDelivery | None


@dataclass
class ConfigTrafficSummary:
    config_id: str
    subscription_id: int
    status_label: str
    is_active: bool
    remaining_days: int
    remaining_bytes: int
    expire_at: datetime


@dataclass
class PaymentApprovalResult:
    payment_request_id: int
    wallet_balance_toman: int
    purchase: PurchaseResult | None


class BotGatewayService:
    def __init__(
        self,
        *,
        subscription_service: SubscriptionService,
        billing_service: BillingService,
        commerce_service: CommerceService,
        openvpn_service: OpenVpnProvisioningService,
        openvpn_endpoint_service: OpenVpnEndpointService,
        server_service: ServerService,
        subscription_base_url: str,
    ):
        self._subscription_service = subscription_service
        self._billing_service = billing_service
        self._commerce_service = commerce_service
        self._openvpn_service = openvpn_service
        self._openvpn_endpoint_service = openvpn_endpoint_service
        self._server_service = server_service
        self._subscription_base_url = subscription_base_url.rstrip("/")

    async def register_user(
        self,
        *,
        telegram_id: str,
        chat_id: str,
        username: str | None = None,
    ) -> User:
        user = await self._subscription_service.get_or_create_user(
            User(
                telegram_id=telegram_id,
                chat_id=chat_id,
                username=username,
            )
        )
        await self._billing_service.get_wallet(user.id)
        return user

    async def get_user_by_telegram(self, telegram_id: str) -> User | None:
        return await self._subscription_service.get_user(GetUserQuery(telegram_id=telegram_id))

    async def list_enabled_services(self):
        return await self._commerce_service.list_service_types(enabled_only=True)

    async def list_plans(self, service_type: str) -> list[Plan]:
        service = await self._commerce_service.get_service_type(service_type)
        if not service or not service.is_enabled:
            raise HTTPException(status_code=404, detail="Service type not available")
        return await self._subscription_service.list_plans(
            ListPlansQuery(service_type=service_type, active_only=True)
        )

    async def get_wallet_balance(self, user_id: int) -> int:
        wallet = await self._billing_service.get_wallet(user_id)
        return wallet.balance_toman

    async def preview_purchase(self, user_id: int, plan_id: int) -> PurchasePreview:
        plan = await self._get_active_plan(plan_id)
        wallet = await self._billing_service.get_wallet(user_id)
        shortfall = max(plan.price_toman - wallet.balance_toman, 0)
        return PurchasePreview(
            plan=plan,
            wallet_balance_toman=wallet.balance_toman,
            price_toman=plan.price_toman,
            sufficient_balance=shortfall == 0,
            shortfall_toman=shortfall,
        )

    async def renew_with_wallet(
        self, user_id: int, subscription_id: int, plan_id: int
    ) -> PurchaseResult:
        return await self._fulfill_renewal_from_wallet(user_id, subscription_id, plan_id)

    async def purchase_with_wallet(self, user_id: int, plan_id: int) -> PurchaseResult:
        preview = await self.preview_purchase(user_id, plan_id)
        if not preview.sufficient_balance:
            raise HTTPException(status_code=400, detail="Insufficient wallet balance")

        await self._billing_service.debit_wallet(
            DebitWalletCommand(
                user_id=user_id,
                amount_toman=preview.plan.price_toman,
                description=f"Purchase {preview.plan.name}",
                reference_type="plan",
                reference_id=plan_id,
            )
        )
        subscription = await self._create_subscription(user_id, preview.plan)
        delivery = await self._try_deliver(subscription)
        wallet = await self._billing_service.get_wallet(user_id)
        return PurchaseResult(
            subscription=subscription,
            wallet_balance_toman=wallet.balance_toman,
            paid_from_wallet=True,
            payment_request_id=None,
            delivery=delivery,
        )

    async def initiate_payment(
        self,
        *,
        user_id: int,
        purpose: PaymentPurpose,
        amount_toman: int,
        payment_method_id: int | None = None,
        plan_id: int | None = None,
        subscription_id: int | None = None,
        service_type: str | None = None,
    ):
        if purpose in {PaymentPurpose.purchase, PaymentPurpose.renewal}:
            if plan_id is None:
                raise HTTPException(status_code=400, detail="plan_id is required")
            plan = await self._get_active_plan(plan_id)
            amount_toman = plan.price_toman
            service_type = plan.service_type
        elif purpose == PaymentPurpose.topup and amount_toman <= 0:
            raise HTTPException(status_code=400, detail="Top-up amount must be positive")

        if payment_method_id is not None:
            method = await self._billing_service.get_payment_method(payment_method_id)
            if not method or not method.is_active:
                raise HTTPException(status_code=404, detail="Payment method not found")

        return await self._billing_service.create_payment_request(
            CreatePaymentRequestCommand(
                user_id=user_id,
                purpose=purpose,
                amount_toman=amount_toman,
                payment_method_id=payment_method_id,
                plan_id=plan_id,
                subscription_id=subscription_id,
                service_type=service_type,
            )
        )

    async def submit_payment_receipt(
        self,
        payment_request_id: int,
        receipt_file_id: str,
        receipt_message_id: int | None = None,
    ):
        return await self._billing_service.submit_payment_receipt(
            SubmitPaymentReceiptCommand(
                payment_request_id=payment_request_id,
                receipt_file_id=receipt_file_id,
                receipt_message_id=receipt_message_id,
            )
        )

    async def list_pending_payments(self):
        return await self._billing_service.list_payment_requests(
            ListPaymentRequestsQuery(status=PaymentRequestStatus.pending_approval.value)
        )

    async def approve_payment(
        self,
        payment_request_id: int,
        reviewer_telegram_id: str,
        admin_note: str = "",
    ) -> PaymentApprovalResult:
        request = await self._billing_service.get_payment_request(payment_request_id)
        if not request:
            raise HTTPException(status_code=404, detail="Payment request not found")

        if request.status == PaymentRequestStatus.completed:
            raise HTTPException(status_code=400, detail="Payment already completed")

        if request.status == PaymentRequestStatus.approved:
            purchase_result = await self._finish_approved_payment(request)
            await self._billing_service.mark_payment_completed(payment_request_id)
            wallet = await self._billing_service.get_wallet(request.user_id)
            return PaymentApprovalResult(
                payment_request_id=payment_request_id,
                wallet_balance_toman=wallet.balance_toman,
                purchase=purchase_result,
            )

        if request.status != PaymentRequestStatus.pending_approval:
            raise HTTPException(status_code=400, detail="Payment request is not pending approval")

        await self._billing_service.credit_wallet(
            CreditWalletCommand(
                user_id=request.user_id,
                amount_toman=request.amount_toman,
                description=f"Payment #{payment_request_id} approved",
                reference_type="payment_request",
                reference_id=payment_request_id,
            )
        )

        try:
            purchase_result = await self._execute_payment_purpose(request)
            await self._billing_service.review_payment_request(
                ReviewPaymentRequestCommand(
                    payment_request_id=payment_request_id,
                    reviewer_telegram_id=reviewer_telegram_id,
                    approve=True,
                    admin_note=admin_note,
                )
            )
            await self._billing_service.mark_payment_completed(payment_request_id)
        except HTTPException:
            await self._billing_service.debit_wallet(
                DebitWalletCommand(
                    user_id=request.user_id,
                    amount_toman=request.amount_toman,
                    description=f"Rollback payment #{payment_request_id} approval",
                    reference_type="payment_request",
                    reference_id=payment_request_id,
                )
            )
            raise

        wallet = await self._billing_service.get_wallet(request.user_id)
        return PaymentApprovalResult(
            payment_request_id=payment_request_id,
            wallet_balance_toman=wallet.balance_toman,
            purchase=purchase_result,
        )

    async def _finish_approved_payment(self, request) -> PurchaseResult | None:
        if request.purpose == PaymentPurpose.topup:
            return None
        if request.purpose == PaymentPurpose.purchase:
            if request.plan_id is None:
                raise HTTPException(status_code=400, detail="Payment request missing plan")
            existing = await self._find_subscription_for_payment(request)
            if existing:
                delivery = await self._try_deliver(existing)
                wallet = await self._billing_service.get_wallet(request.user_id)
                return PurchaseResult(
                    subscription=existing,
                    wallet_balance_toman=wallet.balance_toman,
                    paid_from_wallet=False,
                    payment_request_id=request.id,
                    delivery=delivery,
                )
            return await self._fulfill_purchase_from_wallet(request.user_id, request.plan_id)
        if request.purpose == PaymentPurpose.renewal:
            if request.subscription_id is None or request.plan_id is None:
                raise HTTPException(status_code=400, detail="Payment request missing renewal data")
            return await self._fulfill_renewal_from_wallet(
                request.user_id,
                request.subscription_id,
                request.plan_id,
            )
        return None

    async def _execute_payment_purpose(self, request) -> PurchaseResult | None:
        if request.purpose == PaymentPurpose.topup:
            return None
        if request.purpose == PaymentPurpose.purchase:
            if request.plan_id is None:
                raise HTTPException(status_code=400, detail="Payment request missing plan")
            return await self._fulfill_purchase_from_wallet(request.user_id, request.plan_id)
        if request.purpose == PaymentPurpose.renewal:
            if request.subscription_id is None or request.plan_id is None:
                raise HTTPException(status_code=400, detail="Payment request missing renewal data")
            return await self._fulfill_renewal_from_wallet(
                request.user_id,
                request.subscription_id,
                request.plan_id,
            )
        return None

    async def _find_subscription_for_payment(self, request):
        if request.plan_id is None:
            return None
        subscriptions = await self._subscription_service.list_subscriptions(
            ListSubscriptionsQuery(user_id=request.user_id)
        )
        payment_created = request.created_at
        matches = [
            subscription
            for subscription in subscriptions
            if subscription.plan_id == request.plan_id
            and subscription.status == SubscriptionStatus.active
            and (
                payment_created is None
                or subscription.created_at is None
                or subscription.created_at >= payment_created
            )
        ]
        if not matches:
            return None
        return max(matches, key=lambda item: item.id or 0)

    async def reject_payment(
        self,
        payment_request_id: int,
        reviewer_telegram_id: str,
        admin_note: str = "",
    ):
        return await self._billing_service.review_payment_request(
            ReviewPaymentRequestCommand(
                payment_request_id=payment_request_id,
                reviewer_telegram_id=reviewer_telegram_id,
                approve=False,
                admin_note=admin_note,
            )
        )

    async def list_user_services(self, user_id: int) -> list[UserServiceSummary]:
        subscriptions = await self._subscription_service.list_subscriptions(
            ListSubscriptionsQuery(user_id=user_id)
        )
        summaries: list[UserServiceSummary] = []
        now = datetime.now(UTC)
        for subscription in subscriptions:
            plan = await self._subscription_service.get_plan(
                GetPlanQuery(plan_id=subscription.plan_id)
            )
            remaining_days = max((subscription.expire_at - now).days, 0)
            remaining_bytes = max(
                subscription.traffic_limit_bytes - subscription.traffic_used_bytes,
                0,
            )
            is_active = (
                subscription.status == SubscriptionStatus.active
                and subscription.expire_at > now
                and (
                    subscription.traffic_limit_bytes == 0
                    or subscription.traffic_used_bytes < subscription.traffic_limit_bytes
                )
            )
            status_label = subscription.status.value
            if subscription.expire_at <= now and subscription.status == SubscriptionStatus.active:
                status_label = "expired"
            summaries.append(
                UserServiceSummary(
                    subscription=subscription,
                    plan=plan,
                    is_active=is_active,
                    remaining_days=remaining_days,
                    remaining_bytes=remaining_bytes,
                    status_label=status_label,
                )
            )
        return summaries

    async def get_openvpn_config_traffic(
        self,
        user_id: int,
        config_id: str,
    ) -> ConfigTrafficSummary:
        config_id = config_id.strip()
        if len(config_id) != 10 or not config_id.isdigit():
            raise HTTPException(status_code=400, detail="Config ID must be exactly 10 digits")

        credential = await self._openvpn_service.get_config_by_config_id(user_id, config_id)
        if not credential:
            raise HTTPException(status_code=404, detail="Config not found")

        if not credential.subscription_id:
            raise HTTPException(status_code=404, detail="Subscription not linked to config")

        subscription = await self._subscription_service.get_subscription(
            GetSubscriptionQuery(subscription_id=credential.subscription_id)
        )
        if not subscription or subscription.user_id != user_id:
            raise HTTPException(status_code=404, detail="Subscription not found")

        now = datetime.now(UTC)
        remaining_days = max((subscription.expire_at - now).days, 0)
        remaining_bytes = max(
            subscription.traffic_limit_bytes - subscription.traffic_used_bytes,
            0,
        )
        is_active = (
            credential.status == OpenVpnConfigStatus.active
            and subscription.status == SubscriptionStatus.active
            and subscription.expire_at > now
            and (
                subscription.traffic_limit_bytes == 0
                or subscription.traffic_used_bytes < subscription.traffic_limit_bytes
            )
        )
        status_label = subscription.status.value
        if credential.status != OpenVpnConfigStatus.active:
            status_label = "disabled"
        elif subscription.expire_at <= now and subscription.status == SubscriptionStatus.active:
            status_label = "expired"

        return ConfigTrafficSummary(
            config_id=config_id,
            subscription_id=subscription.id,
            status_label=status_label,
            is_active=is_active,
            remaining_days=remaining_days,
            remaining_bytes=remaining_bytes,
            expire_at=subscription.expire_at,
        )

    async def get_support_info(self):
        return await self._commerce_service.get_bot_settings()

    async def list_payment_methods(self):
        return await self._billing_service.list_payment_methods(active_only=True)

    async def get_active_payment_request(self, user_id: int):
        requests = await self._billing_service.list_payment_requests(
            ListPaymentRequestsQuery(user_id=user_id)
        )
        for request in requests:
            if request.status == PaymentRequestStatus.awaiting_receipt:
                return request
        return None

    async def _fulfill_purchase_from_wallet(self, user_id: int, plan_id: int) -> PurchaseResult:
        plan = await self._get_active_plan(plan_id)
        await self._billing_service.debit_wallet(
            DebitWalletCommand(
                user_id=user_id,
                amount_toman=plan.price_toman,
                description=f"Purchase {plan.name}",
                reference_type="plan",
                reference_id=plan_id,
            )
        )
        try:
            subscription = await self._create_subscription(user_id, plan)
            delivery = await self._try_deliver(subscription)
        except HTTPException:
            await self._billing_service.credit_wallet(
                CreditWalletCommand(
                    user_id=user_id,
                    amount_toman=plan.price_toman,
                    description=f"Rollback purchase {plan.name}",
                    reference_type="plan",
                    reference_id=plan_id,
                )
            )
            raise
        wallet = await self._billing_service.get_wallet(user_id)
        return PurchaseResult(
            subscription=subscription,
            wallet_balance_toman=wallet.balance_toman,
            paid_from_wallet=True,
            payment_request_id=None,
            delivery=delivery,
        )

    async def _fulfill_renewal_from_wallet(
        self,
        user_id: int,
        subscription_id: int,
        plan_id: int,
    ) -> PurchaseResult:
        subscription = await self._subscription_service.get_subscription(
            GetSubscriptionQuery(subscription_id=subscription_id)
        )
        if not subscription or subscription.user_id != user_id:
            raise HTTPException(status_code=404, detail="Subscription not found")

        plan = await self._get_active_plan(plan_id)
        await self._billing_service.debit_wallet(
            DebitWalletCommand(
                user_id=user_id,
                amount_toman=plan.price_toman,
                description=f"Renew {plan.name}",
                reference_type="plan",
                reference_id=plan_id,
            )
        )
        renewed = await self._subscription_service.renew_subscription(
            RenewSubscriptionCommand(subscription_id=subscription_id, plan_id=plan_id)
        )
        if not renewed:
            raise HTTPException(status_code=400, detail="Could not renew subscription")
        delivery = await self._try_deliver(renewed)
        wallet = await self._billing_service.get_wallet(user_id)
        return PurchaseResult(
            subscription=renewed,
            wallet_balance_toman=wallet.balance_toman,
            paid_from_wallet=True,
            payment_request_id=None,
            delivery=delivery,
        )

    async def _create_subscription(self, user_id: int, plan: Plan) -> Subscription:
        subscription = await self._subscription_service.create_subscription(
            CreateSubscriptionCommand(
                user_id=user_id,
                plan_id=plan.id,
                service_type=plan.service_type,
            )
        )
        if not subscription:
            raise HTTPException(status_code=400, detail="Could not create subscription")
        return subscription

    async def _get_active_plan(self, plan_id: int) -> Plan:
        plan = await self._subscription_service.get_plan(GetPlanQuery(plan_id=plan_id))
        if not plan or not plan.is_active:
            raise HTTPException(status_code=404, detail="Plan not found")
        service = await self._commerce_service.get_service_type(plan.service_type)
        if not service or not service.is_enabled:
            raise HTTPException(status_code=400, detail="Service type is disabled")
        return plan

    async def _try_deliver(self, subscription: Subscription) -> ServiceConfigDelivery | None:
        try:
            return await self._deliver_service(subscription)
        except HTTPException as exc:
            LOGGER.warning(
                "Service delivery failed for subscription %s: %s",
                subscription.id,
                exc.detail,
            )
            return None

    async def _deliver_service(self, subscription: Subscription) -> ServiceConfigDelivery:
        if subscription.service_type == "openvpn":
            servers = await self._server_service.list_servers(ListServersQuery())
            server = next(
                (s for s in servers if s.is_active and s.openvpn and s.openvpn.enabled),
                None,
            )
            if not server:
                raise HTTPException(status_code=400, detail="No active OpenVPN server available")
            result = await self._openvpn_service.provision(
                ProvisionOpenVpnCommand(
                    user_id=subscription.user_id,
                    server_id=server.id,
                    subscription_id=subscription.id,
                    config_count=1,
                )
            )
            if not result.credentials:
                raise HTTPException(status_code=500, detail="OpenVPN provisioning failed")
            credential = result.credentials[0]
            return ServiceConfigDelivery(
                service_type=subscription.service_type,
                subscription_id=subscription.id,
                delivery_type="file",
                content=credential.ovpn_content,
                filename=f"{credential.common_name}.ovpn",
            )

        if subscription.service_type == "v2ray":
            url = f"{self._subscription_base_url}/sub/{subscription.uuid}"
            return ServiceConfigDelivery(
                service_type=subscription.service_type,
                subscription_id=subscription.id,
                delivery_type="link",
                content=url,
            )

        raise HTTPException(
            status_code=400,
            detail=f"Unsupported service type: {subscription.service_type}",
        )

    @staticmethod
    def format_bytes(num_bytes: int) -> str:
        if num_bytes >= 1024**3:
            return f"{num_bytes / 1024**3:.2f} GB"
        if num_bytes >= 1024**2:
            return f"{num_bytes / 1024**2:.2f} MB"
        return f"{num_bytes} B"

    async def list_openvpn_servers(self):
        return await self._openvpn_endpoint_service.list_openvpn_servers()

    async def apply_openvpn_endpoint(self, server_id: int, port: int, proto: str) -> dict:
        return await self._openvpn_endpoint_service.apply_endpoint(server_id, port, proto)
