import logging
from datetime import UTC, datetime

from fastapi import HTTPException

from vpn_core.server_management_domain.domain.queries import GetServerQuery, ListServersQuery
from vpn_core.server_management_domain.service import ServerService
from vpn_core.subscription_domain.domain.queries import (
    GetSubscriptionQuery,
    GetUserQuery,
    ListSubscriptionsQuery,
)
from vpn_core.subscription_domain.domain.subscription import SubscriptionStatus
from vpn_core.subscription_domain.repository.base import SubscriptionRepository
from vpn_core.v2ray_sync.client.base import V2RayClient
from vpn_core.v2ray_sync.domain.commands import DeactivateV2RayCommand, ProvisionV2RayCommand
from vpn_core.v2ray_sync.domain.sync_result import ProvisioningResult, SyncOperationResult, SyncStatus
from vpn_core.v2ray_sync.domain.v2ray_client_credential import (
    V2RayClientCredential,
    V2RayConfigStatus,
)
from vpn_core.v2ray_sync.domain.v2ray_user import V2RayUser
from vpn_core.v2ray_sync.repository.base import V2RayCredentialRepository
from vpn_core.v2ray_sync.services.helpers import generate_config_id, node_api_configured
from vpn_core.v2ray_sync.services.v2ray_capacity_service import V2RayCapacityService

LOGGER = logging.getLogger(__name__)


class V2RayProvisioningService:
    """Orchestrates V2Ray account creation via v2ray-node and stores credentials."""

    def __init__(
        self,
        *,
        server_service: ServerService,
        subscription_repository: SubscriptionRepository,
        credential_repository: V2RayCredentialRepository,
        capacity_service: V2RayCapacityService,
        v2ray_client: V2RayClient | None = None,
    ):
        self._server_service = server_service
        self._subscription_repository = subscription_repository
        self._credential_repository = credential_repository
        self._capacity_service = capacity_service
        if v2ray_client is None:
            from vpn_core.v2ray_sync.client.factory import V2RayClientFactory

            v2ray_client = V2RayClientFactory.create()
        self._client = v2ray_client

    def _validate_server(self, server) -> None:
        if not server or not server.is_active:
            raise HTTPException(status_code=404, detail="Server not found or inactive")
        if not node_api_configured(server):
            raise HTTPException(status_code=400, detail="Server does not support V2Ray")
        if not server.xray_inbound_tag:
            raise HTTPException(status_code=400, detail="Server is missing xray_inbound_tag")

    async def provision(self, command: ProvisionV2RayCommand) -> ProvisioningResult:
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
            if subscription.expire_at <= datetime.now(UTC):
                raise HTTPException(status_code=400, detail="Subscription has expired")
        else:
            subs = await self._subscription_repository.list_subscriptions(
                ListSubscriptionsQuery(user_id=command.user_id)
            )
            now = datetime.now(UTC)
            subscription = next(
                (
                    s
                    for s in subs
                    if s.status == SubscriptionStatus.active and s.expire_at > now
                ),
                None,
            )
            if not subscription:
                raise HTTPException(status_code=400, detail="No active subscription for user")

        server = await self._server_service.get_server(GetServerQuery(server_id=command.server_id))
        self._validate_server(server)
        await self._capacity_service.assert_server_has_capacity(command.server_id)

        credentials: list[V2RayClientCredential] = []
        results: list[SyncOperationResult] = []
        existing_count = len(
            await self._credential_repository.list_by_user(
                command.user_id,
                server_id=command.server_id,
            )
        )

        for offset in range(command.config_count):
            email = await self._allocate_config_id(command.server_id)
            slot_index = existing_count + offset
            v2ray_user = V2RayUser(email=email, telegram_id=user.telegram_id)
            try:
                vless_link, client_uuid = await self._client.create_user(server, v2ray_user)
            except Exception as exc:
                LOGGER.exception("V2Ray provisioning failed for %s", email)
                await self._cleanup_failed_provision(server, email=email)
                results.append(
                    SyncOperationResult(
                        operation="create",
                        status=SyncStatus.failed,
                        message=str(exc),
                        server_id=command.server_id,
                        email=email,
                    )
                )
                continue

            credential = V2RayClientCredential(
                user_id=command.user_id,
                subscription_id=subscription.id,
                server_id=command.server_id,
                telegram_id=user.telegram_id,
                email=email,
                client_uuid=client_uuid,
                slot_index=slot_index,
                vless_link=vless_link,
                status=V2RayConfigStatus.active,
            )
            saved = await self._credential_repository.upsert(credential)
            credentials.append(saved)
            results.append(
                SyncOperationResult(
                    operation="create",
                    status=SyncStatus.success,
                    message="V2Ray user provisioned",
                    server_id=command.server_id,
                    email=email,
                    executed_at=datetime.now(UTC).isoformat(),
                )
            )

        if not credentials:
            raise HTTPException(status_code=502, detail="V2Ray provisioning failed on node")

        await self._capacity_service.sync_current_users(command.server_id)
        return ProvisioningResult(credentials=credentials, results=results, idempotent=False)

    async def _allocate_config_id(self, server_id: int) -> str:
        for _ in range(32):
            config_id = generate_config_id()
            existing = await self._credential_repository.get_by_email(server_id, config_id)
            if not existing:
                return config_id
        raise HTTPException(status_code=500, detail="Could not allocate unique config ID")

    async def _cleanup_failed_provision(self, server, *, email: str) -> None:
        if not node_api_configured(server):
            return
        try:
            await self._client.delete_user(server, email)
        except Exception as exc:
            LOGGER.warning("Failed to rollback V2Ray client for %s: %s", email, exc)

    async def get_config_by_config_id(
        self,
        user_id: int,
        config_id: str,
    ) -> V2RayClientCredential | None:
        return await self._credential_repository.get_by_email_for_user(config_id, user_id)

    async def get_configs_for_subscription(
        self,
        user_id: int,
        subscription_id: int,
        *,
        active_only: bool = True,
    ) -> list[V2RayClientCredential]:
        status = V2RayConfigStatus.active if active_only else None
        return await self._credential_repository.list_by_subscription(
            subscription_id,
            user_id=user_id,
            status=status,
        )

    async def deactivate(self, command: DeactivateV2RayCommand) -> int:
        configs = await self._credential_repository.list_by_user(
            command.user_id, status=V2RayConfigStatus.active
        )
        if command.subscription_id is not None:
            configs = [cfg for cfg in configs if cfg.subscription_id == command.subscription_id]
        revoked = 0
        for credential in configs:
            server = await self._server_service.get_server(GetServerQuery(server_id=credential.server_id))
            if server and node_api_configured(server):
                try:
                    await self._client.delete_user(server, credential.email)
                except Exception as exc:
                    LOGGER.warning("Node delete failed for %s: %s", credential.email, exc)
            credential.status = V2RayConfigStatus.revoked
            credential.revoked_at = datetime.now(UTC)
            await self._credential_repository.upsert(credential)
            revoked += 1
        if configs:
            await self._capacity_service.sync_current_users(configs[0].server_id)
        return revoked

    async def list_v2ray_servers(self):
        return await self._server_service.list_servers(
            ListServersQuery(v2ray_enabled=True, is_active=True)
        )

    async def list_configs(
        self,
        user_id: int,
        *,
        server_id: int | None = None,
        active_only: bool = True,
    ) -> list[V2RayClientCredential]:
        status = V2RayConfigStatus.active if active_only else None
        return await self._credential_repository.list_by_user(
            user_id, status=status, server_id=server_id
        )
