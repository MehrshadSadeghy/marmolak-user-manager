import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from vpn_core.openvpn_sync.domain.commands import DeactivateOpenVpnCommand
from vpn_core.openvpn_sync.services.openvpn_provisioning_service import OpenVpnProvisioningService
from vpn_core.subscription_domain.domain.subscription import SubscriptionStatus
from vpn_core.subscription_domain.repository.base import SubscriptionRepository

LOGGER = logging.getLogger(__name__)


@dataclass
class ExpiryEnforcementSummary:
    subscriptions_checked: int = 0
    subscriptions_expired: int = 0
    configs_revoked: int = 0
    errors: list[str] = field(default_factory=list)


class SubscriptionExpiryEnforcementService:
    """Revokes OpenVPN access and marks subscriptions expired when expire_at passes."""

    def __init__(
        self,
        *,
        subscription_repository: SubscriptionRepository,
        provisioning_service: OpenVpnProvisioningService,
    ):
        self._subscription_repository = subscription_repository
        self._provisioning_service = provisioning_service

    async def enforce(self) -> ExpiryEnforcementSummary:
        summary = ExpiryEnforcementSummary()
        expired_candidates = await self._subscription_repository.list_expired_active_subscriptions()
        summary.subscriptions_checked = len(expired_candidates)

        for subscription in expired_candidates:
            if subscription.id is None:
                continue
            try:
                revoked = 0
                if subscription.service_type == "openvpn":
                    revoked = await self._provisioning_service.deactivate(
                        DeactivateOpenVpnCommand(
                            user_id=subscription.user_id,
                            subscription_id=subscription.id,
                            reason="subscription_expired",
                        )
                    )
                subscription.status = SubscriptionStatus.expired
                await self._subscription_repository.update_subscription(subscription)
                summary.subscriptions_expired += 1
                summary.configs_revoked += revoked
                LOGGER.info(
                    "Expired subscription %s for user %s; revoked %s config(s)",
                    subscription.id,
                    subscription.user_id,
                    revoked,
                )
            except Exception as exc:
                LOGGER.exception(
                    "Failed to expire subscription %s for user %s",
                    subscription.id,
                    subscription.user_id,
                )
                summary.errors.append(f"subscription {subscription.id}: {exc}")

        return summary

    @staticmethod
    def is_subscription_expired(subscription, *, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        return subscription.expire_at <= current
