import logging

from fastapi import HTTPException

from vpn_core.openvpn_sync.domain.commands import DeactivateOpenVpnCommand, ReportOpenVpnTrafficCommand
from vpn_core.openvpn_sync.domain.openvpn_traffic import OpenVpnTrafficUsage
from vpn_core.openvpn_sync.repository.base import OpenVpnTrafficRepository
from vpn_core.openvpn_sync.services.openvpn_provisioning_service import OpenVpnProvisioningService
from vpn_core.subscription_domain.domain.queries import GetSubscriptionQuery, GetUserQuery
from vpn_core.subscription_domain.domain.subscription import SubscriptionStatus
from vpn_core.subscription_domain.repository.base import SubscriptionRepository

LOGGER = logging.getLogger(__name__)


class OpenVpnTrafficService:
    """Tracks OpenVPN bandwidth in user-manager and enforces subscription limits."""

    def __init__(
        self,
        *,
        traffic_repository: OpenVpnTrafficRepository,
        subscription_repository: SubscriptionRepository,
        provisioning_service: OpenVpnProvisioningService,
    ):
        self._traffic_repository = traffic_repository
        self._subscription_repository = subscription_repository
        self._provisioning_service = provisioning_service

    async def report_usage(self, command: ReportOpenVpnTrafficCommand) -> OpenVpnTrafficUsage:
        user = await self._subscription_repository.get_user(GetUserQuery(user_id=command.user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        usage = OpenVpnTrafficUsage(
            user_id=command.user_id,
            subscription_id=command.subscription_id,
            bytes_used=command.bytes_used,
        )
        recorded = await self._traffic_repository.add_usage(usage)

        if command.subscription_id:
            await self._enforce_subscription_quota(command.subscription_id)

        return recorded

    async def _enforce_subscription_quota(self, subscription_id: int) -> None:
        subscription = await self._subscription_repository.get_subscription(
            GetSubscriptionQuery(subscription_id=subscription_id)
        )
        if not subscription or subscription.status != SubscriptionStatus.active:
            return

        total = await self._traffic_repository.total_bytes_for_user(
            subscription.user_id,
            subscription_id=subscription_id,
        )
        if subscription.traffic_limit_bytes > 0 and total >= subscription.traffic_limit_bytes:
            subscription.status = SubscriptionStatus.traffic_exceeded
            await self._subscription_repository.update_subscription(subscription)
            await self._provisioning_service.deactivate(
                DeactivateOpenVpnCommand(user_id=subscription.user_id, reason="bandwidth_limit")
            )
            LOGGER.info(
                "Deactivated OpenVPN for user %s due to bandwidth limit",
                subscription.user_id,
            )

    async def get_usage_total(self, user_id: int, subscription_id: int | None = None) -> int:
        return await self._traffic_repository.total_bytes_for_user(user_id, subscription_id)
