import logging
from collections import defaultdict
from dataclasses import dataclass, field

from vpn_core.openvpn_sync.client.base import OpenVpnClient
from vpn_core.openvpn_sync.domain.commands import DeactivateOpenVpnCommand
from vpn_core.openvpn_sync.repository.base import OpenVpnCredentialRepository
from vpn_core.openvpn_sync.services.helpers import node_api_configured
from vpn_core.openvpn_sync.services.openvpn_provisioning_service import OpenVpnProvisioningService
from vpn_core.openvpn_sync.services.traffic_helpers import compute_traffic_delta
from vpn_core.server_management_domain.domain.queries import ListServersQuery
from vpn_core.server_management_domain.service import ServerService
from vpn_core.subscription_domain.domain.queries import GetSubscriptionQuery
from vpn_core.subscription_domain.domain.subscription import SubscriptionStatus
from vpn_core.subscription_domain.repository.base import SubscriptionRepository

LOGGER = logging.getLogger(__name__)


@dataclass
class TrafficEnforcementSummary:
    subscriptions_checked: int = 0
    bytes_accounted: int = 0
    subscriptions_exceeded: int = 0
    configs_revoked: int = 0
    errors: list[str] = field(default_factory=list)


class OpenVpnTrafficEnforcementService:
    """Polls OpenVPN node traffic and revokes configs when plan limits are exceeded."""

    def __init__(
        self,
        *,
        subscription_repository: SubscriptionRepository,
        credential_repository: OpenVpnCredentialRepository,
        provisioning_service: OpenVpnProvisioningService,
        server_service: ServerService,
        openvpn_client: OpenVpnClient,
    ):
        self._subscription_repository = subscription_repository
        self._credential_repository = credential_repository
        self._provisioning_service = provisioning_service
        self._server_service = server_service
        self._client = openvpn_client

    async def sync_and_enforce(self) -> TrafficEnforcementSummary:
        summary = TrafficEnforcementSummary()
        credentials = await self._credential_repository.list_active_with_subscription()
        if not credentials:
            return summary

        by_server: dict[int, list] = defaultdict(list)
        for credential in credentials:
            by_server[credential.server_id].append(credential)

        servers = await self._server_service.list_servers(
            ListServersQuery(openvpn_enabled=True, is_active=True)
        )
        server_map = {server.id: server for server in servers if server.id is not None}

        subscription_deltas: dict[int, int] = defaultdict(int)
        credential_updates: list[tuple[int, int]] = []
        subscriptions_seen: set[int] = set()

        for server_id, server_credentials in by_server.items():
            server = server_map.get(server_id)
            if not server or not node_api_configured(server):
                summary.errors.append(f"Server {server_id} unavailable for traffic sync")
                continue

            try:
                traffic_map = await self._client.fetch_client_traffic(server)
            except Exception as exc:
                LOGGER.exception("Traffic sync failed for server %s", server_id)
                summary.errors.append(f"Server {server_id}: {exc}")
                continue

            for credential in server_credentials:
                if credential.id is None or credential.subscription_id is None:
                    continue

                subscription = await self._subscription_repository.get_subscription(
                    GetSubscriptionQuery(subscription_id=credential.subscription_id)
                )
                if not subscription or subscription.status != SubscriptionStatus.active:
                    continue

                subscriptions_seen.add(subscription.id)
                current_bytes = traffic_map.get(credential.common_name, 0)
                delta = compute_traffic_delta(credential.last_status_bytes, current_bytes)
                if delta > 0:
                    subscription_deltas[credential.subscription_id] += delta
                credential_updates.append((credential.id, current_bytes))

        for subscription_id, delta in subscription_deltas.items():
            subscription = await self._subscription_repository.get_subscription(
                GetSubscriptionQuery(subscription_id=subscription_id)
            )
            if not subscription or subscription.status != SubscriptionStatus.active:
                continue
            subscription.traffic_used_bytes += delta
            summary.bytes_accounted += delta
            await self._subscription_repository.update_subscription(subscription)

        for credential_id, current_bytes in credential_updates:
            await self._credential_repository.update_last_status_bytes(
                credential_id,
                current_bytes,
            )

        for subscription_id in subscriptions_seen:
            subscription = await self._subscription_repository.get_subscription(
                GetSubscriptionQuery(subscription_id=subscription_id)
            )
            if not subscription or subscription.status != SubscriptionStatus.active:
                continue
            if (
                subscription.traffic_limit_bytes > 0
                and subscription.traffic_used_bytes >= subscription.traffic_limit_bytes
            ):
                revoked = await self._provisioning_service.deactivate(
                    DeactivateOpenVpnCommand(
                        user_id=subscription.user_id,
                        subscription_id=subscription.id,
                        reason="bandwidth_limit",
                    )
                )
                subscription.status = SubscriptionStatus.traffic_exceeded
                await self._subscription_repository.update_subscription(subscription)
                summary.subscriptions_exceeded += 1
                summary.configs_revoked += revoked
                LOGGER.info(
                    "Revoked %s OpenVPN config(s) for subscription %s (traffic exceeded)",
                    revoked,
                    subscription.id,
                )

        summary.subscriptions_checked = len(subscriptions_seen)
        return summary
