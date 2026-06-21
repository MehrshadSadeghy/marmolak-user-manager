import logging
from datetime import UTC, datetime

from fastapi import HTTPException

from vpn_core.openvpn_sync.client.base import OpenVpnClient
from vpn_core.openvpn_sync.config import (
    get_openvpn_auto_apply_server_auth,
    get_provisioning_auth_mode,
    get_server_auth_mode,
    provisions_without_client_cert,
)
from vpn_core.openvpn_sync.domain.auth_mode import OpenVpnAuthMode
from vpn_core.openvpn_sync.domain.commands import DeactivateOpenVpnCommand, ProvisionOpenVpnCommand
from vpn_core.openvpn_sync.domain.openvpn_client_credential import (
    OpenVpnClientCredential,
    OpenVpnConfigStatus,
)
from vpn_core.openvpn_sync.domain.openvpn_user import OpenVpnUser
from vpn_core.openvpn_sync.domain.sync_result import ProvisioningResult, SyncOperationResult, SyncStatus
from vpn_core.openvpn_sync.repository.base import OpenVpnCredentialRepository
from vpn_core.openvpn_sync.services.helpers import generate_config_id, node_api_configured
from vpn_core.openvpn_sync.services.openvpn_migration_helpers import (
    can_finalize_auth_migration,
    can_migrate_legacy_credential,
)
from vpn_core.openvpn_sync.services.password_service import PasswordService
from vpn_core.openvpn_sync.services.server_capacity_service import ServerCapacityService
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
        capacity_service: ServerCapacityService,
        password_service: PasswordService | None = None,
        openvpn_client: OpenVpnClient | None = None,
    ):
        self._server_service = server_service
        self._subscription_repository = subscription_repository
        self._credential_repository = credential_repository
        self._capacity_service = capacity_service
        self._password_service = password_service or PasswordService()
        if openvpn_client is None:
            from vpn_core.openvpn_sync.client.factory import OpenVpnClientFactory

            openvpn_client = OpenVpnClientFactory.create()
        self._client = openvpn_client

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

        auth_mode = get_provisioning_auth_mode()
        server_auth_mode = get_server_auth_mode()
        if auth_mode != OpenVpnAuthMode.certificate and get_openvpn_auto_apply_server_auth():
            await self._client.apply_auth_mode(server, server_auth_mode.value)

        credentials: list[OpenVpnClientCredential] = []
        results: list[SyncOperationResult] = []
        ephemeral_passwords: dict[str, str] = {}
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
            plaintext_password: str | None = None
            password_hash: str | None = None
            auth_synced_at: datetime | None = None

            if auth_mode != OpenVpnAuthMode.certificate:
                plaintext_password = self._password_service.generate_password()
                password_hash = self._password_service.hash_password(plaintext_password)

            auth_user_created = False
            cert_created = False
            issues_client_cert = not provisions_without_client_cert(auth_mode)
            try:
                if auth_mode != OpenVpnAuthMode.certificate:
                    await self._client.create_auth_user(server, config_id, password_hash)
                    auth_user_created = True
                    auth_synced_at = datetime.now(UTC)

                ovpn_content = await self._client.create_user(
                    server,
                    ovpn_user,
                    auth_mode=auth_mode.value,
                )
                if issues_client_cert:
                    cert_created = True
            except Exception as exc:
                LOGGER.exception("OpenVPN provisioning failed for %s", config_id)
                await self._cleanup_failed_provision(
                    server,
                    config_id=config_id,
                    auth_user_created=auth_user_created,
                    cert_created=cert_created,
                )
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
                auth_mode=auth_mode,
                vpn_username=config_id if auth_mode != OpenVpnAuthMode.certificate else None,
                password_hash=password_hash,
                auth_synced_at=auth_synced_at,
                status=OpenVpnConfigStatus.active,
            )
            saved = await self._credential_repository.upsert(credential)
            credentials.append(saved)
            if plaintext_password:
                ephemeral_passwords[config_id] = plaintext_password
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

        await self._capacity_service.sync_current_users(command.server_id)

        return ProvisioningResult(
            credentials=credentials,
            results=results,
            idempotent=False,
            ephemeral_passwords=ephemeral_passwords,
        )

    async def _allocate_config_id(self, server_id: int) -> str:
        for _ in range(32):
            config_id = generate_config_id()
            existing = await self._credential_repository.get_by_common_name(server_id, config_id)
            if not existing:
                return config_id
        raise HTTPException(status_code=500, detail="Could not allocate unique config ID")

    async def _cleanup_failed_provision(
        self,
        server,
        *,
        config_id: str,
        auth_user_created: bool,
        cert_created: bool,
    ) -> None:
        if not node_api_configured(server):
            return
        if cert_created:
            try:
                await self._client.delete_user(server, config_id)
            except Exception as exc:
                LOGGER.warning("Failed to rollback cert for %s: %s", config_id, exc)
        if auth_user_created:
            try:
                await self._client.delete_auth_user(server, config_id)
            except Exception as exc:
                LOGGER.warning("Failed to rollback auth user for %s: %s", config_id, exc)

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

    async def _revoke_credential_on_node(
        self,
        server,
        credential: OpenVpnClientCredential,
    ) -> None:
        if not node_api_configured(server):
            return

        if credential.auth_mode == OpenVpnAuthMode.certificate:
            try:
                await self._client.delete_user(server, credential.common_name)
            except Exception as exc:
                LOGGER.warning(
                    "Node cert delete failed for %s: %s",
                    credential.common_name,
                    exc,
                )
            return

        username = credential.vpn_username or credential.common_name
        try:
            await self._client.delete_auth_user(server, username)
        except Exception as exc:
            LOGGER.warning("Node auth delete failed for %s: %s", username, exc)

        if credential.auth_mode == OpenVpnAuthMode.dual:
            try:
                await self._client.delete_user(server, credential.common_name)
            except Exception as exc:
                LOGGER.warning(
                    "Node cert delete failed for %s: %s",
                    credential.common_name,
                    exc,
                )

    async def deactivate(self, command: DeactivateOpenVpnCommand) -> int:
        configs = await self._credential_repository.list_by_user(
            command.user_id, status=OpenVpnConfigStatus.active
        )
        if command.subscription_id is not None:
            configs = [cfg for cfg in configs if cfg.subscription_id == command.subscription_id]
        revoked = 0
        for cfg in configs:
            server = await self._server_service.get_server(GetServerQuery(server_id=cfg.server_id))
            if server:
                await self._revoke_credential_on_node(server, cfg)
            if await self._credential_repository.revoke(cfg.id):
                revoked += 1
                await self._capacity_service.sync_current_users(cfg.server_id)
        return revoked

    async def rotate_password(
        self,
        user_id: int,
        config_id: str,
    ) -> tuple[OpenVpnClientCredential, str]:
        config_id = config_id.strip()
        credential = await self._credential_repository.get_by_common_name_for_user(config_id, user_id)
        if not credential or credential.user_id != user_id:
            raise HTTPException(status_code=404, detail="Configuration not found")
        if credential.auth_mode == OpenVpnAuthMode.certificate:
            raise HTTPException(
                status_code=400,
                detail="Password recovery is not available for certificate-only configs",
            )

        username = credential.vpn_username or credential.common_name
        plaintext_password = self._password_service.generate_password()
        password_hash = self._password_service.hash_password(plaintext_password)

        server = await self._server_service.get_server(GetServerQuery(server_id=credential.server_id))
        self._validate_server(server)
        try:
            await self._client.rotate_auth_user(server, username, password_hash)
        except Exception as exc:
            LOGGER.exception("OpenVPN password rotation failed for %s", username)
            raise HTTPException(status_code=502, detail="Failed to rotate OpenVPN password on node") from exc

        credential.password_hash = password_hash
        credential.password_rotated_at = datetime.now(UTC)
        credential.auth_synced_at = datetime.now(UTC)
        saved = await self._credential_repository.upsert(credential)
        return saved, plaintext_password

    async def migrate_legacy_to_auth(
        self,
        user_id: int,
        config_id: str,
    ) -> tuple[OpenVpnClientCredential, str]:
        config_id = config_id.strip()
        credential = await self._credential_repository.get_by_common_name_for_user(config_id, user_id)
        if not credential or credential.user_id != user_id:
            raise HTTPException(status_code=404, detail="Configuration not found")
        if not can_migrate_legacy_credential(credential):
            raise HTTPException(
                status_code=400,
                detail="Legacy migration is not available for this configuration",
            )

        username = credential.common_name
        plaintext_password = self._password_service.generate_password()
        password_hash = self._password_service.hash_password(plaintext_password)
        now = datetime.now(UTC)

        server = await self._server_service.get_server(GetServerQuery(server_id=credential.server_id))
        self._validate_server(server)

        try:
            await self._client.create_auth_user(server, username, password_hash)
            ovpn_user = OpenVpnUser(common_name=username, telegram_id=credential.telegram_id)
            ovpn_content = await self._client.create_user(
                server,
                ovpn_user,
                auth_mode=OpenVpnAuthMode.dual.value,
            )
        except Exception as exc:
            LOGGER.exception("OpenVPN legacy migration failed for %s", username)
            try:
                await self._client.delete_auth_user(server, username)
            except Exception as rollback_exc:
                LOGGER.warning("Failed to rollback auth user for %s: %s", username, rollback_exc)
            raise HTTPException(status_code=502, detail="Failed to migrate OpenVPN credentials on node") from exc

        credential.auth_mode = OpenVpnAuthMode.dual
        credential.vpn_username = username
        credential.password_hash = password_hash
        credential.password_rotated_at = now
        credential.auth_synced_at = now
        credential.ovpn_content = ovpn_content
        saved = await self._credential_repository.upsert(credential)
        return saved, plaintext_password

    async def finalize_auth_migration(
        self,
        user_id: int,
        config_id: str,
    ) -> OpenVpnClientCredential:
        config_id = config_id.strip()
        credential = await self._credential_repository.get_by_common_name_for_user(config_id, user_id)
        if not credential or credential.user_id != user_id:
            raise HTTPException(status_code=404, detail="Configuration not found")
        if not can_finalize_auth_migration(credential):
            raise HTTPException(
                status_code=400,
                detail="Certificate removal is not available yet for this configuration",
            )

        username = credential.vpn_username or credential.common_name
        server = await self._server_service.get_server(GetServerQuery(server_id=credential.server_id))
        self._validate_server(server)

        try:
            await self._client.delete_user(server, credential.common_name)
            ovpn_user = OpenVpnUser(common_name=credential.common_name, telegram_id=credential.telegram_id)
            ovpn_content = await self._client.create_user(
                server,
                ovpn_user,
                auth_mode=OpenVpnAuthMode.user_pass.value,
            )
        except Exception as exc:
            LOGGER.exception("OpenVPN auth migration finalize failed for %s", username)
            raise HTTPException(
                status_code=502,
                detail="Failed to finalize OpenVPN auth migration on node",
            ) from exc

        credential.auth_mode = OpenVpnAuthMode.user_pass
        credential.ovpn_content = ovpn_content
        credential.auth_synced_at = datetime.now(UTC)
        return await self._credential_repository.upsert(credential)
