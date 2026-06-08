from abc import ABC, abstractmethod

from vpn_core.user_admin_domain.domain.models import (
    AdminAuditLogEntry,
    AdminUserConfigDetail,
    AdminUserConfigItem,
    AdminUserDetail,
    AdminUserListItem,
    CollaboratorDiscountRule,
    PaginatedUsers,
)


class UserAdminRepository(ABC):
    @abstractmethod
    async def list_users_paginated(
        self,
        *,
        page: int,
        page_size: int,
        query: str | None = None,
    ) -> PaginatedUsers:
        pass

    @abstractmethod
    async def get_user_detail(self, user_id: int) -> AdminUserDetail | None:
        pass

    @abstractmethod
    async def list_user_configs(self, user_id: int) -> list[AdminUserConfigItem]:
        pass

    @abstractmethod
    async def get_user_config_detail(
        self,
        user_id: int,
        config_id: str,
    ) -> AdminUserConfigDetail | None:
        pass

    @abstractmethod
    async def count_active_configs(self, user_id: int) -> int:
        pass

    @abstractmethod
    async def list_discount_rules(self, user_id: int) -> list[CollaboratorDiscountRule]:
        pass

    @abstractmethod
    async def upsert_discount_rule(
        self,
        user_id: int,
        service_type: str,
        discount_percent: int,
    ) -> CollaboratorDiscountRule:
        pass

    @abstractmethod
    async def delete_discount_rules(self, user_id: int) -> int:
        pass

    @abstractmethod
    async def delete_discount_rule(self, user_id: int, service_type: str) -> bool:
        pass

    @abstractmethod
    async def create_audit_log(self, entry: AdminAuditLogEntry) -> AdminAuditLogEntry:
        pass

    @abstractmethod
    async def get_discount_percent(self, user_id: int, service_type: str) -> int | None:
        pass
