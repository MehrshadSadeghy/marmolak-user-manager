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
from vpn_core.openvpn_sync.domain.auth_mode import OpenVpnAuthMode
from vpn_core.openvpn_sync.domain.commands import ProvisionOpenVpnCommand
from vpn_core.openvpn_sync.domain.openvpn_client_credential import OpenVpnConfigStatus
from vpn_core.openvpn_sync.services.openvpn_credential_delivery_service import OpenVpnCredentialDeliveryService
from vpn_core.openvpn_sync.services.openvpn_endpoint_service import OpenVpnEndpointService
from vpn_core.openvpn_sync.services.openvpn_migration_helpers import (
    can_finalize_auth_migration,
    can_migrate_legacy_credential,
)
from vpn_core.openvpn_sync.services.openvpn_provisioning_service import OpenVpnProvisioningService
from vpn_core.v2ray_sync.domain.commands import ProvisionV2RayCommand
from vpn_core.v2ray_sync.services.v2ray_capacity_service import V2RayCapacityService
from vpn_core.v2ray_sync.services.v2ray_provisioning_service import V2RayProvisioningService
from vpn_core.openvpn_sync.services.server_capacity_service import ServerCapacityService
from vpn_core.openvpn_sync.services.openvpn_traffic_enforcement_service import (
    OpenVpnTrafficEnforcementService,
)
from vpn_core.openvpn_sync.services.subscription_expiry_enforcement_service import (
    SubscriptionExpiryEnforcementService,
)
from vpn_core.server_management_domain.domain.queries import GetServerQuery, ListServersQuery
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
from vpn_core.user_admin_domain.service import UserAdminService
from vpn_core.client_subscription_domain.service import ClientSubscriptionService
from vpn_core.v2ray_sync.services.v2ray_inbound_config_service import V2RayInboundConfigService


@dataclass
class ServiceConfigDelivery:
    service_type: str
    subscription_id: int
    delivery_type: str
    content: str
    filename: str | None = None
    config_id: str | None = None
    username: str | None = None
    password: str | None = None
    includes_password: bool = False
    server_host: str | None = None
    server_port: int | None = None
    server_proto: str | None = None
    expire_at: str | None = None
    traffic_limit_bytes: int | None = None
    traffic_used_bytes: int | None = None
    remaining_bytes: int | None = None
    remaining_days: int | None = None
    auth_mode: str | None = None


@dataclass
class UserServiceSummary:
    subscription: Subscription
    plan: Plan | None
    is_active: bool
    remaining_days: int
    remaining_bytes: int
    status_label: str
    config_ids: list[str]
    migratable_config_ids: list[str] = None
    finalizable_config_ids: list[str] = None
    password_config_ids: list[str] = None

    def __post_init__(self) -> None:
        if self.migratable_config_ids is None:
            self.migratable_config_ids = []
        if self.finalizable_config_ids is None:
            self.finalizable_config_ids = []
        if self.password_config_ids is None:
            self.password_config_ids = []


@dataclass
class PurchasePreview:
    plan: Plan
    wallet_balance_toman: int
    price_toman: int
    sufficient_balance: bool
    shortfall_toman: int
    original_price_toman: int | None = None
    discount_percent: int | None = None


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
    traffic_used_bytes: int
    traffic_limit_bytes: int
    remaining_bytes: int
    expire_at: datetime


@dataclass
class PaymentApprovalResult:
    payment_request_id: int
    wallet_balance_toman: int
    purchase: PurchaseResult | None
    user_telegram_id: str
    user_chat_id: str
    purpose: str


class BotGatewayService:
    def __init__(
        self,
        *,
        subscription_service: SubscriptionService,
        billing_service: BillingService,
        commerce_service: CommerceService,
        openvpn_service: OpenVpnProvisioningService,
        v2ray_service: V2RayProvisioningService,
        openvpn_endpoint_service: OpenVpnEndpointService,
        server_service: ServerService,
        capacity_service: ServerCapacityService,
        v2ray_capacity_service: V2RayCapacityService,
        user_admin_service: UserAdminService,
        traffic_enforcement_service: OpenVpnTrafficEnforcementService,
        expiry_enforcement_service: SubscriptionExpiryEnforcementService,
        openvpn_delivery_service: OpenVpnCredentialDeliveryService,
        subscription_base_url: str,
        client_subscription_service: ClientSubscriptionService | None = None,
        v2ray_inbound_config_service: V2RayInboundConfigService | None = None,
    ):
        self._subscription_service = subscription_service
        self._billing_service = billing_service
        self._commerce_service = commerce_service
        self._openvpn_service = openvpn_service
        self._v2ray_service = v2ray_service
        self._openvpn_endpoint_service = openvpn_endpoint_service
        self._openvpn_delivery_service = openvpn_delivery_service
        self._server_service = server_service
        self._capacity_service = capacity_service
        self._v2ray_capacity_service = v2ray_capacity_service
        self._user_admin_service = user_admin_service
        self._traffic_enforcement_service = traffic_enforcement_service
        self._expiry_enforcement_service = expiry_enforcement_service
        self._subscription_base_url = subscription_base_url.rstrip("/")
        self._client_subscription_service = client_subscription_service
        self._v2ray_inbound_config_service = v2ray_inbound_config_service

    async def get_client_subscription_url(self, user_id: int) -> str:
        if not self._client_subscription_service:
            raise HTTPException(status_code=503, detail="Client subscription is not configured")
        return await self._client_subscription_service.get_subscription_url_for_user(user_id)

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

    async def list_plans(self, service_type: str, user_id: int | None = None) -> list[Plan]:
        service = await self._commerce_service.get_service_type(service_type)
        if not service or not service.is_enabled:
            raise HTTPException(status_code=404, detail="Service type not available")
        plans = await self._subscription_service.list_plans(
            ListPlansQuery(service_type=service_type, active_only=True)
        )
        if user_id is None:
            return plans
        discounted: list[Plan] = []
        for plan in plans:
            discounted.append(await self._apply_plan_discount(user_id, plan))
        return discounted

    async def get_user_access_status(self, user_id: int) -> dict:
        blocked = await self._user_admin_service.is_user_blocked(user_id)
        return {"user_id": user_id, "is_blocked": blocked}

    async def get_wallet_balance(self, user_id: int) -> int:
        wallet = await self._billing_service.get_wallet(user_id)
        return wallet.balance_toman

    async def preview_purchase(
        self,
        user_id: int,
        plan_id: int,
        *,
        server_id: int | None = None,
    ) -> PurchasePreview:
        await self._user_admin_service.assert_user_not_blocked(user_id)
        plan = await self._get_active_plan(plan_id)
        await self._validate_server_for_purchase(plan, server_id, require_server=False)
        discounted_plan = await self._apply_plan_discount(user_id, plan)
        price_toman, discount_percent = await self._user_admin_service.apply_discounted_price(
            user_id,
            plan,
        )
        wallet = await self._billing_service.get_wallet(user_id)
        shortfall = max(price_toman - wallet.balance_toman, 0)
        return PurchasePreview(
            plan=discounted_plan,
            wallet_balance_toman=wallet.balance_toman,
            price_toman=price_toman,
            sufficient_balance=shortfall == 0,
            shortfall_toman=shortfall,
            original_price_toman=plan.price_toman if discount_percent else None,
            discount_percent=discount_percent,
        )

    async def renew_with_wallet(
        self, user_id: int, subscription_id: int, plan_id: int
    ) -> PurchaseResult:
        await self._user_admin_service.assert_user_not_blocked(user_id)
        return await self._fulfill_renewal_from_wallet(user_id, subscription_id, plan_id)

    async def purchase_with_wallet(
        self,
        user_id: int,
        plan_id: int,
        *,
        server_id: int | None = None,
    ) -> PurchaseResult:
        preview = await self.preview_purchase(user_id, plan_id, server_id=server_id)
        if preview.plan.service_type == "openvpn" and server_id is None:
            raise HTTPException(status_code=400, detail="server_id is required for OpenVPN purchase")
        if preview.plan.service_type == "v2ray" and server_id is None:
            raise HTTPException(status_code=400, detail="server_id is required for V2Ray purchase")
        if not preview.sufficient_balance:
            raise HTTPException(status_code=400, detail="Insufficient wallet balance")

        await self._billing_service.debit_wallet(
            DebitWalletCommand(
                user_id=user_id,
                amount_toman=preview.price_toman,
                description=f"Purchase {preview.plan.name}",
                reference_type="plan",
                reference_id=plan_id,
            )
        )
        subscription = await self._create_subscription(user_id, preview.plan)
        delivery = await self._ensure_delivery_for_subscription(subscription, server_id=server_id)
        if not delivery:
            LOGGER.error(
                "Service delivery failed after wallet purchase for subscription %s",
                subscription.id,
            )
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
        await self._user_admin_service.assert_user_not_blocked(user_id)
        if purpose in {PaymentPurpose.purchase, PaymentPurpose.renewal}:
            if plan_id is None:
                raise HTTPException(status_code=400, detail="plan_id is required")
            plan = await self._get_active_plan(plan_id)
            amount_toman, _ = await self._user_admin_service.apply_discounted_price(user_id, plan)
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
            await self._billing_service.mark_payment_completed(payment_request_id)
            return await self._build_payment_approval_result(
                payment_request_id=payment_request_id,
                user_id=request.user_id,
                purchase=None,
                purpose=request.purpose,
            )

        if request.status != PaymentRequestStatus.pending_approval:
            raise HTTPException(status_code=400, detail="Payment request is not pending approval")

        try:
            await self._billing_service.credit_wallet(
                CreditWalletCommand(
                    user_id=request.user_id,
                    amount_toman=request.amount_toman,
                    description=f"Payment #{payment_request_id} approved",
                    reference_type="payment_request",
                    reference_id=payment_request_id,
                )
            )
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

        return await self._build_payment_approval_result(
            payment_request_id=payment_request_id,
            user_id=request.user_id,
            purchase=None,
            purpose=request.purpose,
        )

    async def _build_payment_approval_result(
        self,
        *,
        payment_request_id: int,
        user_id: int,
        purchase: PurchaseResult | None,
        purpose: PaymentPurpose,
    ) -> PaymentApprovalResult:
        user = await self._subscription_service.get_user(GetUserQuery(user_id=user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        wallet = await self._billing_service.get_wallet(user_id)
        return PaymentApprovalResult(
            payment_request_id=payment_request_id,
            wallet_balance_toman=wallet.balance_toman,
            purchase=purchase,
            user_telegram_id=user.telegram_id,
            user_chat_id=user.chat_id,
            purpose=purpose.value,
        )

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
        try:
            await self._expiry_enforcement_service.enforce()
        except Exception:
            LOGGER.exception("Expiry enforcement failed before listing user services")

        try:
            await self._traffic_enforcement_service.sync_and_enforce()
        except Exception:
            LOGGER.exception("Live traffic sync failed before listing user services")

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
            if subscription.status == SubscriptionStatus.expired:
                status_label = "expired"
            elif subscription.expire_at <= now and subscription.status == SubscriptionStatus.active:
                status_label = "expired"
            summaries.append(
                UserServiceSummary(
                    subscription=subscription,
                    plan=plan,
                    is_active=is_active,
                    remaining_days=remaining_days,
                    remaining_bytes=remaining_bytes,
                    status_label=status_label,
                    config_ids=await self._config_ids_for_subscription(
                        user_id,
                        subscription.id,
                        subscription.service_type,
                    ),
                    **await self._openvpn_migration_config_ids(
                        user_id,
                        subscription.id,
                        subscription.service_type,
                    ),
                )
            )
        return summaries

    async def _config_ids_for_subscription(
        self,
        user_id: int,
        subscription_id: int | None,
        service_type: str,
    ) -> list[str]:
        if subscription_id is None:
            return []
        if service_type == "openvpn":
            credentials = await self._openvpn_service.get_configs_for_subscription(
                user_id,
                subscription_id,
            )
            return [credential.common_name for credential in credentials if self._is_valid_ovpn(credential.ovpn_content)]

        if service_type == "v2ray":
            credentials = await self._v2ray_service.get_configs_for_subscription(
                user_id,
                subscription_id,
            )
            return [
                credential.email
                for credential in credentials
                if self._is_valid_proxy_link(credential.vless_link)
            ]
        return []

    async def _openvpn_migration_config_ids(
        self,
        user_id: int,
        subscription_id: int | None,
        service_type: str,
    ) -> dict[str, list[str]]:
        if subscription_id is None or service_type != "openvpn":
            return {"migratable_config_ids": [], "finalizable_config_ids": [], "password_config_ids": []}

        credentials = await self._openvpn_service.get_configs_for_subscription(
            user_id,
            subscription_id,
        )
        migratable: list[str] = []
        finalizable: list[str] = []
        password_configs: list[str] = []
        for credential in credentials:
            if not self._is_valid_ovpn(credential.ovpn_content):
                continue
            if credential.auth_mode != OpenVpnAuthMode.certificate:
                password_configs.append(credential.common_name)
            if can_migrate_legacy_credential(credential):
                migratable.append(credential.common_name)
            if can_finalize_auth_migration(credential):
                finalizable.append(credential.common_name)
        return {
            "migratable_config_ids": migratable,
            "finalizable_config_ids": finalizable,
            "password_config_ids": password_configs,
        }

    async def get_subscription_delivery(
        self,
        user_id: int,
        subscription_id: int,
    ) -> ServiceConfigDelivery:
        subscription = await self._subscription_service.get_subscription(
            GetSubscriptionQuery(subscription_id=subscription_id)
        )
        if not subscription or subscription.user_id != user_id:
            raise HTTPException(status_code=404, detail="Subscription not found")
        delivery = await self._ensure_delivery_for_subscription(subscription)
        if not delivery:
            raise HTTPException(status_code=404, detail="Configuration not available for this service")
        return delivery

    async def get_first_openvpn_delivery(self, user_id: int) -> ServiceConfigDelivery:
        summaries = await self.list_user_services(user_id)
        for item in summaries:
            if item.subscription.service_type != "openvpn":
                continue
            try:
                return await self.get_subscription_delivery(user_id, item.subscription.id)
            except HTTPException:
                continue
        raise HTTPException(status_code=404, detail="No OpenVPN configuration available")

    async def get_openvpn_config_delivery(
        self,
        user_id: int,
        config_id: str,
    ) -> ServiceConfigDelivery:
        config_id = config_id.strip()
        if len(config_id) != 10 or not config_id.isdigit():
            raise HTTPException(status_code=400, detail="Config ID must be exactly 10 digits")

        credential = await self._openvpn_service.get_config_by_config_id(user_id, config_id)
        if not credential or credential.user_id != user_id:
            raise HTTPException(status_code=404, detail="Configuration not found")
        if not self._is_valid_ovpn(credential.ovpn_content):
            subscription_id = credential.subscription_id or 0
            if subscription_id:
                subscription = await self._subscription_service.get_subscription(
                    GetSubscriptionQuery(subscription_id=subscription_id)
                )
                if subscription:
                    return await self.get_subscription_delivery(user_id, subscription_id)
            raise HTTPException(status_code=404, detail="Configuration not available")
        if not credential.subscription_id:
            raise HTTPException(status_code=404, detail="Subscription not linked to config")

        subscription = await self._subscription_service.get_subscription(
            GetSubscriptionQuery(subscription_id=credential.subscription_id)
        )
        if not subscription or subscription.user_id != user_id:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return await self._build_openvpn_delivery(subscription, credential)

    async def get_v2ray_config_delivery(
        self,
        user_id: int,
        config_id: str,
    ) -> ServiceConfigDelivery:
        config_id = config_id.strip()
        if len(config_id) != 10 or not config_id.isdigit():
            raise HTTPException(status_code=400, detail="Config ID must be exactly 10 digits")

        credential = await self._v2ray_service.get_config_by_config_id(user_id, config_id)
        if not credential or credential.user_id != user_id:
            raise HTTPException(status_code=404, detail="Configuration not found")
        if not self._is_valid_proxy_link(credential.vless_link):
            subscription_id = credential.subscription_id or 0
            if subscription_id:
                subscription = await self._subscription_service.get_subscription(
                    GetSubscriptionQuery(subscription_id=subscription_id)
                )
                if subscription:
                    return await self.get_subscription_delivery(user_id, subscription_id)
            raise HTTPException(status_code=404, detail="Configuration not available")
        if not credential.subscription_id:
            raise HTTPException(status_code=404, detail="Subscription not linked to config")

        subscription = await self._subscription_service.get_subscription(
            GetSubscriptionQuery(subscription_id=credential.subscription_id)
        )
        if not subscription or subscription.user_id != user_id:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return ServiceConfigDelivery(
            service_type=subscription.service_type,
            subscription_id=subscription.id,
            delivery_type="link",
            content=credential.vless_link,
            config_id=credential.email,
        )

    async def get_openvpn_credential_view(
        self,
        user_id: int,
        config_id: str,
    ) -> ServiceConfigDelivery:
        config_id = config_id.strip()
        if len(config_id) != 10 or not config_id.isdigit():
            raise HTTPException(status_code=400, detail="Config ID must be exactly 10 digits")

        credential = await self._openvpn_service.get_config_by_config_id(user_id, config_id)
        if not credential:
            raise HTTPException(status_code=404, detail="Configuration not found")
        subscription = await self._subscription_service.get_subscription(
            GetSubscriptionQuery(subscription_id=credential.subscription_id)
        )
        if not subscription or subscription.user_id != user_id:
            raise HTTPException(status_code=404, detail="Subscription not found")

        payload = await self._openvpn_delivery_service.build_delivery(
            subscription,
            credential,
            include_ovpn_file=False,
        )
        return ServiceConfigDelivery(**payload)

    async def rotate_openvpn_credentials(
        self,
        user_id: int,
        config_id: str,
    ) -> ServiceConfigDelivery:
        credential, plaintext_password = await self._openvpn_service.rotate_password(user_id, config_id)
        subscription = await self._subscription_service.get_subscription(
            GetSubscriptionQuery(subscription_id=credential.subscription_id)
        )
        if not subscription or subscription.user_id != user_id:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return await self._build_openvpn_delivery(
            subscription,
            credential,
            ephemeral_password=plaintext_password,
        )

    async def migrate_openvpn_credentials(
        self,
        user_id: int,
        config_id: str,
    ) -> ServiceConfigDelivery:
        credential, plaintext_password = await self._openvpn_service.migrate_legacy_to_auth(
            user_id,
            config_id,
        )
        subscription = await self._subscription_service.get_subscription(
            GetSubscriptionQuery(subscription_id=credential.subscription_id)
        )
        if not subscription or subscription.user_id != user_id:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return await self._build_openvpn_delivery(
            subscription,
            credential,
            ephemeral_password=plaintext_password,
        )

    async def finalize_openvpn_auth_migration(
        self,
        user_id: int,
        config_id: str,
    ) -> ServiceConfigDelivery:
        credential = await self._openvpn_service.finalize_auth_migration(user_id, config_id)
        subscription = await self._subscription_service.get_subscription(
            GetSubscriptionQuery(subscription_id=credential.subscription_id)
        )
        if not subscription or subscription.user_id != user_id:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return await self._build_openvpn_delivery(subscription, credential)

    async def get_openvpn_config_traffic(
        self,
        user_id: int,
        config_id: str,
    ) -> ConfigTrafficSummary:
        config_id = config_id.strip()
        if len(config_id) != 10 or not config_id.isdigit():
            raise HTTPException(status_code=400, detail="Config ID must be exactly 10 digits")

        try:
            await self._expiry_enforcement_service.enforce()
        except Exception:
            LOGGER.exception("Expiry enforcement failed before config-traffic lookup")

        try:
            await self._traffic_enforcement_service.sync_and_enforce()
        except Exception:
            LOGGER.exception("Live traffic sync failed before config-traffic lookup")

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
        elif subscription.status == SubscriptionStatus.expired:
            status_label = "expired"
        elif subscription.expire_at <= now and subscription.status == SubscriptionStatus.active:
            status_label = "expired"

        return ConfigTrafficSummary(
            config_id=config_id,
            subscription_id=subscription.id,
            status_label=status_label,
            is_active=is_active,
            remaining_days=remaining_days,
            traffic_used_bytes=subscription.traffic_used_bytes,
            traffic_limit_bytes=subscription.traffic_limit_bytes,
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

    async def _fulfill_purchase_from_wallet(
        self,
        user_id: int,
        plan_id: int,
        *,
        server_id: int | None = None,
    ) -> PurchaseResult:
        plan = await self._get_active_plan(plan_id)
        await self._validate_server_for_purchase(plan, server_id, require_server=True)
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
            delivery = await self._try_deliver(subscription, server_id=server_id)
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
        price_toman, _ = await self._user_admin_service.apply_discounted_price(user_id, plan)
        await self._billing_service.debit_wallet(
            DebitWalletCommand(
                user_id=user_id,
                amount_toman=price_toman,
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

    async def _apply_plan_discount(self, user_id: int, plan: Plan) -> Plan:
        price_toman, discount_percent = await self._user_admin_service.apply_discounted_price(
            user_id,
            plan,
        )
        if discount_percent is None:
            return plan
        return plan.model_copy(update={"price_toman": price_toman})

    async def _get_active_plan(self, plan_id: int) -> Plan:
        plan = await self._subscription_service.get_plan(GetPlanQuery(plan_id=plan_id))
        if not plan or not plan.is_active:
            raise HTTPException(status_code=404, detail="Plan not found")
        service = await self._commerce_service.get_service_type(plan.service_type)
        if not service or not service.is_enabled:
            raise HTTPException(status_code=400, detail="Service type is disabled")
        return plan

    async def _try_deliver(
        self,
        subscription: Subscription,
        *,
        server_id: int | None = None,
    ) -> ServiceConfigDelivery | None:
        delivery = await self._ensure_delivery_for_subscription(subscription, server_id=server_id)
        if delivery:
            return delivery
        LOGGER.error(
            "Service delivery failed for subscription %s: no configuration could be produced",
            subscription.id,
        )
        return None

    @staticmethod
    def _is_valid_ovpn(content: str) -> bool:
        if not content or "MOCK-CA" in content:
            return False
        if "<ca>" in content:
            return True
        return "auth-user-pass" in content

    async def _build_openvpn_delivery(
        self,
        subscription: Subscription,
        credential,
        *,
        ephemeral_password: str | None = None,
        include_ovpn_file: bool = True,
    ) -> ServiceConfigDelivery:
        payload = await self._openvpn_delivery_service.build_delivery(
            subscription,
            credential,
            ephemeral_password=ephemeral_password,
            include_ovpn_file=include_ovpn_file,
        )
        return ServiceConfigDelivery(**payload)

    @staticmethod
    def _is_valid_proxy_link(content: str) -> bool:
        return ClientSubscriptionService.is_valid_proxy_link(content)

    @staticmethod
    def _is_valid_vless_link(content: str) -> bool:
        return bool(content and content.startswith("vless://"))

    async def _delivery_from_existing_credentials(
        self,
        subscription: Subscription,
    ) -> ServiceConfigDelivery | None:
        if subscription.id is None:
            return None
        if subscription.service_type == "openvpn":
            credentials = await self._openvpn_service.get_configs_for_subscription(
                subscription.user_id,
                subscription.id,
            )
            for credential in credentials:
                if self._is_valid_ovpn(credential.ovpn_content):
                    return await self._build_openvpn_delivery(subscription, credential)
            return None

        if subscription.service_type == "v2ray":
            credentials = await self._v2ray_service.get_configs_for_subscription(
                subscription.user_id,
                subscription.id,
            )
            for credential in credentials:
                if self._is_valid_proxy_link(credential.vless_link):
                    return ServiceConfigDelivery(
                        service_type=subscription.service_type,
                        subscription_id=subscription.id,
                        delivery_type="link",
                        content=credential.vless_link,
                        config_id=credential.email,
                    )
        return None

    async def _ensure_delivery_for_subscription(
        self,
        subscription: Subscription,
        *,
        server_id: int | None = None,
    ) -> ServiceConfigDelivery | None:
        existing = await self._delivery_from_existing_credentials(subscription)
        if existing:
            return existing
        try:
            return await self._deliver_service(
                subscription,
                allow_existing=False,
                server_id=server_id,
            )
        except HTTPException as exc:
            LOGGER.error(
                "Service provisioning failed for subscription %s: %s",
                subscription.id,
                exc.detail,
            )
            return await self._delivery_from_existing_credentials(subscription)

    async def _deliver_service(
        self,
        subscription: Subscription,
        *,
        allow_existing: bool = True,
        server_id: int | None = None,
    ) -> ServiceConfigDelivery:
        if allow_existing:
            existing = await self._delivery_from_existing_credentials(subscription)
            if existing:
                return existing

        if subscription.service_type == "openvpn":
            server = await self._resolve_openvpn_server(server_id)
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
            if not self._is_valid_ovpn(credential.ovpn_content):
                raise HTTPException(
                    status_code=502,
                    detail="OpenVPN node returned invalid configuration (check MOCK_MODE=false)",
                )
            ephemeral_password = result.ephemeral_passwords.get(credential.common_name)
            return await self._build_openvpn_delivery(
                subscription,
                credential,
                ephemeral_password=ephemeral_password,
            )

        if subscription.service_type == "v2ray":
            server = await self._resolve_v2ray_server(server_id)
            result = await self._v2ray_service.provision(
                ProvisionV2RayCommand(
                    user_id=subscription.user_id,
                    server_id=server.id,
                    subscription_id=subscription.id,
                    config_count=1,
                )
            )
            if not result.credentials:
                raise HTTPException(status_code=500, detail="V2Ray provisioning failed")
            credential = result.credentials[0]
            if not self._is_valid_proxy_link(credential.vless_link):
                raise HTTPException(
                    status_code=502,
                    detail="V2Ray node returned invalid configuration (check MOCK_MODE=false)",
                )
            return ServiceConfigDelivery(
                service_type=subscription.service_type,
                subscription_id=subscription.id,
                delivery_type="link",
                content=credential.vless_link,
                config_id=credential.email,
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
        servers = await self._openvpn_endpoint_service.list_openvpn_servers()
        summaries = []
        for server in servers:
            if server.id is None:
                continue
            snapshot = await self._capacity_service.get_server_capacity_snapshot(server)
            summaries.append(
                {
                    "server": server,
                    "max_users": snapshot.max_users,
                    "current_users": snapshot.current_users,
                    "is_full": snapshot.is_full,
                    "remaining_slots": snapshot.remaining_slots,
                }
            )
        return summaries

    async def list_v2ray_servers(self):
        servers = await self._v2ray_service.list_v2ray_servers()
        summaries = []
        for server in servers:
            if server.id is None:
                continue
            snapshot = await self._v2ray_capacity_service.get_server_capacity_snapshot(server)
            summaries.append(
                {
                    "server": server,
                    "max_users": snapshot.max_users,
                    "current_users": snapshot.current_users,
                    "is_full": snapshot.is_full,
                    "remaining_slots": snapshot.remaining_slots,
                }
            )
        return summaries

    async def _validate_server_for_purchase(
        self,
        plan: Plan,
        server_id: int | None,
        *,
        require_server: bool = False,
    ) -> None:
        if plan.service_type == "openvpn":
            if server_id is None:
                if require_server:
                    raise HTTPException(
                        status_code=400,
                        detail="server_id is required for OpenVPN purchase",
                    )
                return
            await self._resolve_openvpn_server(server_id)
            await self._capacity_service.assert_server_has_capacity(server_id)
            return

        if plan.service_type == "v2ray":
            if server_id is None:
                if require_server:
                    raise HTTPException(
                        status_code=400,
                        detail="server_id is required for V2Ray purchase",
                    )
                return
            await self._resolve_v2ray_server(server_id)
            await self._v2ray_capacity_service.assert_server_has_capacity(server_id)

    async def _validate_openvpn_server_for_purchase(
        self,
        plan: Plan,
        server_id: int | None,
        *,
        require_server: bool = False,
    ) -> None:
        await self._validate_server_for_purchase(
            plan,
            server_id,
            require_server=require_server,
        )

    async def _resolve_v2ray_server(self, server_id: int | None):
        if server_id is None:
            raise HTTPException(status_code=400, detail="server_id is required for V2Ray")
        server = await self._server_service.get_server(GetServerQuery(server_id=server_id))
        if not server or not server.is_active or not server.v2ray.enabled:
            raise HTTPException(status_code=400, detail="V2Ray server not available")
        if not server.xray_inbound_tag:
            raise HTTPException(status_code=400, detail="V2Ray server is missing xray_inbound_tag")
        return server

    async def _resolve_openvpn_server(self, server_id: int | None):
        if server_id is None:
            raise HTTPException(status_code=400, detail="server_id is required for OpenVPN")
        server = await self._server_service.get_server(GetServerQuery(server_id=server_id))
        if not server or not server.is_active or not server.openvpn.enabled:
            raise HTTPException(status_code=400, detail="OpenVPN server not available")
        return server

    async def apply_openvpn_endpoint(self, server_id: int, port: int, proto: str) -> dict:
        return await self._openvpn_endpoint_service.apply_endpoint(server_id, port, proto)

    async def get_v2ray_inbound_config(self, server_id: int) -> dict:
        if not self._v2ray_inbound_config_service:
            raise HTTPException(status_code=503, detail="V2Ray inbound config is not configured")
        return await self._v2ray_inbound_config_service.get_inbound_config(server_id)

    async def patch_v2ray_inbound_config(self, server_id: int, payload: dict) -> dict:
        if not self._v2ray_inbound_config_service:
            raise HTTPException(status_code=503, detail="V2Ray inbound config is not configured")
        return await self._v2ray_inbound_config_service.apply_inbound_config(
            server_id,
            payload,
            partial=True,
        )
