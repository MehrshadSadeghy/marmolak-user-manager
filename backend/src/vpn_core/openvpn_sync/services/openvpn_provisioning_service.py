import logging
from datetime import UTC, datetime

from fastapi import HTTPException

from vpn_core.openvpn_sync.client.factory import OpenVpnClientFactory
from vpn_core.openvpn_sync.domain.commands import DeactivateOpenVpnCommand, ProvisionOpenVpnCommand
from vpn_core.openvpn_sync.domain.openvpn_client_credential import (
    OpenVpnClientCredential,
    OpenVpnConfigStatus,
)
from vpn_core.openvpn_sync.domain.openvpn_user import OpenVpnUser
from vpn_core.openvpn_sync.domain.sync_result import ProvisioningResult, SyncOperationResult, SyncStatus
from vpn_core.openvpn_sync.repository.base import OpenVpnCredentialRepository
from vpn_core.openvpn_sync.services.helpers import build_common_name, node_api_configured
from vpn_core.server_management_domain.domain.queries import GetServerQuery
from vpn_core.server_management_domain.service import ServerService
from vpn_core.subscription_domain.domain.queries import (
    GetSubscriptionQuery,
    GetUserQuery,
    ListSubscriptionsQuery,
)
from vpn_core.subscription_domain.domain.subscription import SubscriptionStatus
from vpn_core.subscription_domain.repository.base import SubscriptionRepository

LOGGER = logging.getLogger(__name__)


class OpenVpnProvisioningService:
    """Orchestrates OpenVPN account creation via vpn-node and stores credentials."""

    def __init__(
        self,
        *,
        server_service: ServerService,
        subscription_repository: SubscriptionRepository,
        credential_repository: OpenVpnCredentialRepository,
    ):
        self._server_service = server_service
        self._subscription_repository = subscription_repository
        self._credential_repository = credential_repository
        self._client = OpenVpnClientFactory.create()

    def _validate_server(self, server) -> None:
        if not server or not server.is_active:
            raise HTTPException(status_code=404, detail="Server not found or inactive")
        if not node_api_configured(server):
            raise HTTPException(status_code=400, detail="Server does not support OpenVPN")

    async def provision(self, command: ProvisionOpenVpnCommand) -> ProvisioningResult:
        user = await self._subscription_repository.get_user(GetUserQuery(user_id=command.user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if command.subscription_id:
            subscription = await self._subscription_repository.get_subscription(
                GetSubscriptionQuery(subscription_id=command.subscription_id)
            )
            if not subscription or subscription.user_id != command.user_id:
                raise HTTPException(status_code=404, detail="Subscription not found")
            if subscription.status != SubscriptionStatus.active:
                raise HTTPException(status_code=400, detail="Subscription is not active")
        else:
            subs = await self._subscription_repository.list_subscriptions(
                ListSubscriptionsQuery(user_id=command.user_id)
            )
            subscription = next((s for s in subs if s.status == SubscriptionStatus.active), None)
            if not subscription:
                raise HTTPException(status_code=400, detail="No active subscription for user")

        server = await self._server_service.get_server(GetServerQuery(server_id=command.server_id))
        self._validate_server(server)

        credentials: list[OpenVpnClientCredential] = []
        results: list[SyncOperationResult] = []
        any_idempotent = False

        for slot in range(command.config_count):
            common_name = build_common_name(user.telegram_id, slot)
            existing = await self._credential_repository.get_by_common_name(
                command.server_id, common_name
            )
            if existing and existing.status == OpenVpnConfigStatus.active:
                credentials.append(existing)
                results.append(
                    SyncOperationResult(
                        operation="create",
                        status=SyncStatus.skipped,
                        message="User already provisioned (idempotent skip)",
                        server_id=command.server_id,
                        common_name=common_name,
                    )
                )
                any_idempotent = True
                continue

            ovpn_user = OpenVpnUser(common_name=common_name, telegram_id=user.telegram_id)
            try:
                ovpn_content = await self._client.create_user(server, ovpn_user)
            except Exception as exc:
                LOGGER.exception("OpenVPN provisioning failed for %s", common_name)
                results.append(
                    SyncOperationResult(
                        operation="create",
                        status=SyncStatus.failed,
                        message=str(exc),
                        server_id=command.server_id,
                        common_name=common_name,
                    )
                )
                continue

            credential = OpenVpnClientCredential(
                user_id=command.user_id,
                subscription_id=subscription.id,
                server_id=command.server_id,
                telegram_id=user.telegram_id,
                common_name=common_name,
                slot_index=slot,
                ovpn_content=ovpn_content,
                status=OpenVpnConfigStatus.active,
            )
            saved = await self._credential_repository.upsert(credential)
            credentials.append(saved)
            results.append(
                SyncOperationResult(
                    operation="create",
                    status=SyncStatus.success,
                    message="OpenVPN user provisioned",
                    server_id=command.server_id,
                    common_name=common_name,
                    executed_at=datetime.now(UTC),
                )
            )

        if not credentials:
            raise HTTPException(status_code=502, detail="OpenVPN provisioning failed on node")

        return ProvisioningResult(
            credentials=credentials,
            results=results,
            idempotent=any_idempotent and len(credentials) == command.config_count,
        )

    async def list_configs(
        self,
        user_id: int,
        *,
        server_id: int | None = None,
        active_only: bool = True,
    ) -> list[OpenVpnClientCredential]:
        status = OpenVpnConfigStatus.active if active_only else None
        return await self._credential_repository.list_by_user(
            user_id, status=status, server_id=server_id
        )

    async def get_config(self, credential_id: int) -> OpenVpnClientCredential | None:
        return await self._credential_repository.get_by_id(credential_id)

    async def deactivate(self, command: DeactivateOpenVpnCommand) -> int:
        configs = await self._credential_repository.list_by_user(
            command.user_id, status=OpenVpnConfigStatus.active
        )
        revoked = 0
        for cfg in configs:
            server = await self._server_service.get_server(GetServerQuery(server_id=cfg.server_id))
            if server and node_api_configured(server):
                try:
                    await self._client.delete_user(server, cfg.common_name)
                except Exception as exc:
                    LOGGER.warning("Node delete failed for %s: %s", cfg.common_name, exc)
            if await self._credential_repository.revoke(cfg.id):
                revoked += 1
        return revoked
