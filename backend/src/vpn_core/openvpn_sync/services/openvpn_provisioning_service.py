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
from vpn_core.openvpn_sync.services.helpers import generate_config_id, node_api_configured
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
        existing_count = len(
            await self._credential_repository.list_by_user(
                command.user_id,
                server_id=command.server_id,
            )
        )

        for offset in range(command.config_count):
            config_id = await self._allocate_config_id(command.server_id)
            slot_index = existing_count + offset

            ovpn_user = OpenVpnUser(common_name=config_id, telegram_id=user.telegram_id)
            try:
                ovpn_content = await self._client.create_user(server, ovpn_user)
            except Exception as exc:
                LOGGER.exception("OpenVPN provisioning failed for %s", config_id)
                results.append(
                    SyncOperationResult(
                        operation="create",
                        status=SyncStatus.failed,
                        message=str(exc),
                        server_id=command.server_id,
                        common_name=config_id,
                    )
                )
                continue

            credential = OpenVpnClientCredential(
                user_id=command.user_id,
                subscription_id=subscription.id,
                server_id=command.server_id,
                telegram_id=user.telegram_id,
                common_name=config_id,
                slot_index=slot_index,
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
                    common_name=config_id,
                    executed_at=datetime.now(UTC),
                )
            )

        if not credentials:
            raise HTTPException(status_code=502, detail="OpenVPN provisioning failed on node")

        return ProvisioningResult(
            credentials=credentials,
            results=results,
            idempotent=False,
        )

    async def _allocate_config_id(self, server_id: int) -> str:
        for _ in range(32):
            config_id = generate_config_id()
            existing = await self._credential_repository.get_by_common_name(server_id, config_id)
            if not existing:
                return config_id
        raise HTTPException(status_code=500, detail="Could not allocate unique config ID")

    async def get_config_by_config_id(
        self,
        user_id: int,
        config_id: str,
    ) -> OpenVpnClientCredential | None:
        return await self._credential_repository.get_by_common_name_for_user(config_id, user_id)

    async def get_configs_for_subscription(
        self,
        user_id: int,
        subscription_id: int,
        *,
        active_only: bool = True,
    ) -> list[OpenVpnClientCredential]:
        status = OpenVpnConfigStatus.active if active_only else None
        return await self._credential_repository.list_by_subscription(
            subscription_id,
            user_id=user_id,
            status=status,
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
