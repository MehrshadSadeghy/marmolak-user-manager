from datetime import UTC, datetime

from fastapi import HTTPException

from vpn_core.openvpn_sync.domain.commands import ProvisionOpenVpnCommand
from vpn_core.openvpn_sync.domain.openvpn_client_credential import OpenVpnConfigStatus
from vpn_core.openvpn_sync.repository.base import OpenVpnCredentialRepository
from vpn_core.openvpn_sync.services.openvpn_provisioning_service import OpenVpnProvisioningService
from vpn_core.server_management_domain.domain.queries import GetServerQuery
from vpn_core.server_management_domain.service import ServerService
from vpn_core.subscription_domain.domain.queries import GetUserQuery
from vpn_core.subscription_domain.domain.user import User
from vpn_core.subscription_domain.repository.base import SubscriptionRepository
from vpn_core.user_admin_domain.domain.audit_action import AdminAuditAction
from vpn_core.user_admin_domain.domain.models import (
    AdminAuditLogEntry,
    AdminUserConfigDetail,
    AdminUserConfigItem,
    AdminUserDetail,
    CollaboratorDiscountRule,
    PaginatedUsers,
)
from vpn_core.user_admin_domain.repository.base import UserAdminRepository

USER_PAGE_SIZE_DEFAULT = 20
ALLOWED_DISCOUNT_PERCENTS = {5, 10, 15, 20, 30}


class UserAdminService:
    def __init__(
        self,
        *,
        user_admin_repository: UserAdminRepository,
        subscription_repository: SubscriptionRepository,
        credential_repository: OpenVpnCredentialRepository,
        openvpn_service: OpenVpnProvisioningService,
        server_service: ServerService,
    ):
        self._user_admin_repository = user_admin_repository
        self._subscription_repository = subscription_repository
        self._credential_repository = credential_repository
        self._openvpn_service = openvpn_service
        self._server_service = server_service

    async def list_users(
        self,
        *,
        page: int = 1,
        page_size: int = USER_PAGE_SIZE_DEFAULT,
        query: str | None = None,
    ) -> PaginatedUsers:
        return await self._user_admin_repository.list_users_paginated(
            page=page,
            page_size=page_size,
            query=query,
        )

    async def get_user_detail(self, user_id: int) -> AdminUserDetail:
        detail = await self._user_admin_repository.get_user_detail(user_id)
        if not detail:
            raise HTTPException(status_code=404, detail="User not found")
        return detail

    async def list_user_configs(self, user_id: int) -> list[AdminUserConfigItem]:
        await self._require_user(user_id)
        return await self._user_admin_repository.list_user_configs(user_id)

    async def get_user_config_detail(self, user_id: int, config_id: str) -> AdminUserConfigDetail:
        detail = await self._user_admin_repository.get_user_config_detail(user_id, config_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Config not found")
        return detail

    async def block_user(
        self,
        user_id: int,
        *,
        admin_telegram_id: str,
        reason: str | None = None,
    ) -> AdminUserDetail:
        user = await self._require_user(user_id)
        if user.is_blocked:
            return await self.get_user_detail(user_id)

        user.is_blocked = True
        user.is_active = False
        user.blocked_at = datetime.now(UTC)
        user.blocked_reason = reason
        user.blocked_by_admin_telegram_id = admin_telegram_id
        await self._subscription_repository.update_user(user)

        await self._log_action(
            admin_telegram_id=admin_telegram_id,
            action=AdminAuditAction.user_blocked,
            target_user_id=user_id,
            details={"reason": reason},
        )
        return await self.get_user_detail(user_id)

    async def unblock_user(self, user_id: int, *, admin_telegram_id: str) -> AdminUserDetail:
        user = await self._require_user(user_id)
        if not user.is_blocked:
            return await self.get_user_detail(user_id)

        user.is_blocked = False
        user.is_active = True
        user.blocked_at = None
        user.blocked_reason = None
        user.blocked_by_admin_telegram_id = None
        await self._subscription_repository.update_user(user)

        await self._log_action(
            admin_telegram_id=admin_telegram_id,
            action=AdminAuditAction.user_unblocked,
            target_user_id=user_id,
        )
        return await self.get_user_detail(user_id)

    async def enable_config(
        self,
        user_id: int,
        config_id: str,
        *,
        admin_telegram_id: str,
    ) -> AdminUserConfigDetail:
        credential = await self._require_config(user_id, config_id)
        if credential.status == OpenVpnConfigStatus.revoked:
            raise HTTPException(status_code=400, detail="Revoked config cannot be enabled")
        if credential.status == OpenVpnConfigStatus.active:
            return await self.get_user_config_detail(user_id, config_id)

        updated = await self._credential_repository.set_status(
            credential.id,
            OpenVpnConfigStatus.active,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Config not found")

        await self._log_action(
            admin_telegram_id=admin_telegram_id,
            action=AdminAuditAction.config_enabled,
            target_user_id=user_id,
            target_config_id=config_id,
        )
        return await self.get_user_config_detail(user_id, config_id)

    async def disable_config(
        self,
        user_id: int,
        config_id: str,
        *,
        admin_telegram_id: str,
    ) -> AdminUserConfigDetail:
        credential = await self._require_config(user_id, config_id)
        if credential.status != OpenVpnConfigStatus.active:
            return await self.get_user_config_detail(user_id, config_id)

        updated = await self._credential_repository.set_status(
            credential.id,
            OpenVpnConfigStatus.disabled,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Config not found")

        await self._log_action(
            admin_telegram_id=admin_telegram_id,
            action=AdminAuditAction.config_disabled,
            target_user_id=user_id,
            target_config_id=config_id,
        )
        return await self.get_user_config_detail(user_id, config_id)

    async def regenerate_config(
        self,
        user_id: int,
        config_id: str,
        *,
        admin_telegram_id: str,
    ) -> AdminUserConfigDetail:
        credential = await self._require_config(user_id, config_id)
        if not credential.subscription_id:
            raise HTTPException(status_code=400, detail="Config is not linked to a subscription")

        await self._credential_repository.set_status(credential.id, OpenVpnConfigStatus.revoked)

        result = await self._openvpn_service.provision(
            ProvisionOpenVpnCommand(
                user_id=user_id,
                server_id=credential.server_id,
                subscription_id=credential.subscription_id,
                config_count=1,
            )
        )
        if not result.credentials:
            raise HTTPException(status_code=502, detail="Config regeneration failed")

        new_config_id = result.credentials[0].common_name
        await self._log_action(
            admin_telegram_id=admin_telegram_id,
            action=AdminAuditAction.config_regenerated,
            target_user_id=user_id,
            target_config_id=config_id,
            details={"new_config_id": new_config_id},
        )
        return await self.get_user_config_detail(user_id, new_config_id)

    async def add_collaborator_discount(
        self,
        user_id: int,
        *,
        admin_telegram_id: str,
        discount_percent: int,
        service_type: str,
    ) -> AdminUserDetail:
        if discount_percent not in ALLOWED_DISCOUNT_PERCENTS:
            raise HTTPException(status_code=400, detail="Invalid discount percentage")
        user = await self._require_user(user_id)

        existing_rules = await self._user_admin_repository.list_discount_rules(user_id)
        had_rule = any(rule.service_type == service_type for rule in existing_rules)

        await self._user_admin_repository.upsert_discount_rule(
            user_id,
            service_type,
            discount_percent,
        )
        if not user.is_collaborator:
            user.is_collaborator = True
            await self._subscription_repository.update_user(user)

        await self._log_action(
            admin_telegram_id=admin_telegram_id,
            action=(
                AdminAuditAction.collaborator_discount_changed
                if had_rule
                else AdminAuditAction.collaborator_added
            ),
            target_user_id=user_id,
            details={
                "service_type": service_type,
                "discount_percent": discount_percent,
            },
        )
        return await self.get_user_detail(user_id)

    async def remove_collaborator(self, user_id: int, *, admin_telegram_id: str) -> AdminUserDetail:
        user = await self._require_user(user_id)
        deleted = await self._user_admin_repository.delete_discount_rules(user_id)
        if user.is_collaborator or deleted:
            user.is_collaborator = False
            await self._subscription_repository.update_user(user)
            await self._log_action(
                admin_telegram_id=admin_telegram_id,
                action=AdminAuditAction.collaborator_removed,
                target_user_id=user_id,
                details={"removed_rules": deleted},
            )
        return await self.get_user_detail(user_id)

    async def list_discount_rules(self, user_id: int) -> list[CollaboratorDiscountRule]:
        return await self._user_admin_repository.list_discount_rules(user_id)

    async def get_collaborator_discount_percent(
        self,
        user_id: int,
        service_type: str,
    ) -> int | None:
        return await self._user_admin_repository.get_discount_percent(user_id, service_type)

    async def apply_discounted_price(self, user_id: int, plan) -> tuple[int, int | None]:
        percent = await self.get_collaborator_discount_percent(user_id, plan.service_type)
        if percent is None:
            return plan.price_toman, None
        discounted = max(int(plan.price_toman * (100 - percent) / 100), 0)
        return discounted, percent

    async def is_user_blocked(self, user_id: int) -> bool:
        user = await self._subscription_repository.get_user(GetUserQuery(user_id=user_id))
        return bool(user and user.is_blocked)

    async def assert_user_not_blocked(self, user_id: int) -> None:
        if await self.is_user_blocked(user_id):
            raise HTTPException(
                status_code=403,
                detail="Your account has been blocked by an administrator",
            )

    async def _require_user(self, user_id: int) -> User:
        user = await self._subscription_repository.get_user(GetUserQuery(user_id=user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    async def _require_config(self, user_id: int, config_id: str):
        credential = await self._credential_repository.get_by_common_name_for_user(config_id, user_id)
        if not credential:
            raise HTTPException(status_code=404, detail="Config not found")
        return credential

    async def _log_action(
        self,
        *,
        admin_telegram_id: str,
        action: AdminAuditAction,
        target_user_id: int | None = None,
        target_config_id: str | None = None,
        details: dict | None = None,
    ) -> None:
        await self._user_admin_repository.create_audit_log(
            AdminAuditLogEntry(
                admin_telegram_id=admin_telegram_id,
                action=action.value,
                target_user_id=target_user_id,
                target_config_id=target_config_id,
                details=details,
            )
        )
