import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime

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
    disconnect_events_accounted: int = 0
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
        consumed_disconnects: dict[int, list[str]] = defaultdict(list)

        for server_id, server_credentials in by_server.items():
            server = server_map.get(server_id)
            if not server or not node_api_configured(server):
                summary.errors.append(f"Server {server_id} unavailable for traffic sync")
                continue

            try:
                snapshot = await self._client.fetch_client_traffic(server)
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
                if subscription.expire_at <= datetime.now(UTC):
                    continue

                subscriptions_seen.add(subscription.id)
                common_name = credential.common_name

                pending_total = snapshot.disconnect.get(common_name)
                if pending_total is not None:
                    delta = compute_traffic_delta(
                        credential.last_status_bytes,
                        pending_total,
                    )
                    if delta > 0:
                        subscription_deltas[credential.subscription_id] += delta
                        summary.bytes_accounted += delta
                    credential_updates.append((credential.id, 0))
                    consumed_disconnects[server_id].append(common_name)
                    summary.disconnect_events_accounted += 1
                    continue

                current_bytes = snapshot.live.get(common_name, 0)
                if current_bytes <= 0:
                    continue

                delta = compute_traffic_delta(credential.last_status_bytes, current_bytes)
                if delta > 0:
                    subscription_deltas[credential.subscription_id] += delta
                    summary.bytes_accounted += delta
                credential_updates.append((credential.id, current_bytes))

        for subscription_id, delta in subscription_deltas.items():
            subscription = await self._subscription_repository.get_subscription(
                GetSubscriptionQuery(subscription_id=subscription_id)
            )
            if not subscription or subscription.status != SubscriptionStatus.active:
                continue
            if subscription.expire_at <= datetime.now(UTC):
                continue
            subscription.traffic_used_bytes += delta
            await self._subscription_repository.update_subscription(subscription)

        for credential_id, current_bytes in credential_updates:
            await self._credential_repository.update_last_status_bytes(
                credential_id,
                current_bytes,
            )

        for server_id, common_names in consumed_disconnects.items():
            server = server_map.get(server_id)
            if not server:
                continue
            try:
                await self._client.consume_disconnect_traffic(server, common_names)
            except Exception as exc:
                LOGGER.warning(
                    "Failed to consume disconnect traffic for server %s: %s",
                    server_id,
                    exc,
                )
                summary.errors.append(f"Server {server_id} disconnect consume: {exc}")

        for subscription_id in subscriptions_seen:
            subscription = await self._subscription_repository.get_subscription(
                GetSubscriptionQuery(subscription_id=subscription_id)
            )
            if not subscription or subscription.status != SubscriptionStatus.active:
                continue
            if subscription.expire_at <= datetime.now(UTC):
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
