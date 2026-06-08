import math

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from vpn_core.openvpn_sync.db_model.openvpn_client_credential import OpenVpnClientCredentialORM
from vpn_core.openvpn_sync.domain.openvpn_client_credential import OpenVpnConfigStatus
from vpn_core.subscription_domain.db_model.subscription import Subscription as SubscriptionORM
from vpn_core.subscription_domain.db_model.user import User as UserORM
from vpn_core.user_admin_domain.db_model.admin_audit_log import AdminAuditLog as AdminAuditLogORM
from vpn_core.user_admin_domain.db_model.collaborator_discount_rule import (
    CollaboratorDiscountRule as CollaboratorDiscountRuleORM,
)
from vpn_core.user_admin_domain.domain.models import (
    AdminAuditLogEntry,
    AdminUserConfigDetail,
    AdminUserConfigItem,
    AdminUserDetail,
    AdminUserListItem,
    CollaboratorDiscountRule,
    PaginatedUsers,
)
from vpn_core.user_admin_domain.repository.base import UserAdminRepository


def _normalize_search_query(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = raw.strip().lstrip("@")
    return cleaned or None


def _config_status_label(status: str) -> str:
    if status == OpenVpnConfigStatus.active.value:
        return "Active"
    return "Disabled"


class UserAdminDBRepository(UserAdminRepository):
    def __init__(self, session: Session):
        self._session = session

    def _active_config_count_subquery(self):
        return (
            self._session.query(
                OpenVpnClientCredentialORM.user_id,
                func.count(OpenVpnClientCredentialORM.id).label("active_count"),
            )
            .filter(OpenVpnClientCredentialORM.status == OpenVpnConfigStatus.active.value)
            .group_by(OpenVpnClientCredentialORM.user_id)
            .subquery()
        )

    async def list_users_paginated(
        self,
        *,
        page: int,
        page_size: int,
        query: str | None = None,
    ) -> PaginatedUsers:
        page = max(page, 1)
        page_size = max(min(page_size, 100), 1)
        active_counts = self._active_config_count_subquery()

        db_query = self._session.query(
            UserORM,
            func.coalesce(active_counts.c.active_count, 0).label("active_configs_count"),
        ).outerjoin(active_counts, UserORM.id == active_counts.c.user_id)

        normalized = _normalize_search_query(query)
        if normalized:
            filters = [
                UserORM.username.ilike(f"%{normalized}%"),
                UserORM.telegram_id == normalized,
            ]
            if normalized.isdigit():
                numeric = int(normalized)
                filters.append(UserORM.id == numeric)
                filters.append(UserORM.telegram_id == str(numeric))
            db_query = db_query.filter(or_(*filters))

        total_items = db_query.count()
        rows = (
            db_query.order_by(UserORM.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        items = [
            AdminUserListItem(
                id=user.id,
                telegram_id=user.telegram_id,
                username=user.username,
                created_at=user.created_at,
                active_configs_count=int(active_count or 0),
                is_blocked=user.is_blocked,
                is_collaborator=user.is_collaborator,
            )
            for user, active_count in rows
        ]
        total_pages = max(math.ceil(total_items / page_size), 1)
        return PaginatedUsers(
            items=items,
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
        )

    async def get_user_detail(self, user_id: int) -> AdminUserDetail | None:
        user = self._session.get(UserORM, user_id)
        if not user:
            return None

        total_purchased = (
            self._session.query(func.count(SubscriptionORM.id))
            .filter(SubscriptionORM.user_id == user_id)
            .scalar()
            or 0
        )
        total_active_configs = (
            self._session.query(func.count(OpenVpnClientCredentialORM.id))
            .filter(
                OpenVpnClientCredentialORM.user_id == user_id,
                OpenVpnClientCredentialORM.status == OpenVpnConfigStatus.active.value,
            )
            .scalar()
            or 0
        )
        total_traffic = (
            self._session.query(func.coalesce(func.sum(SubscriptionORM.traffic_used_bytes), 0))
            .filter(SubscriptionORM.user_id == user_id)
            .scalar()
            or 0
        )
        rules = await self.list_discount_rules(user_id)
        return AdminUserDetail(
            id=user.id,
            telegram_id=user.telegram_id,
            username=user.username,
            created_at=user.created_at,
            total_purchased_plans=int(total_purchased),
            total_active_configs=int(total_active_configs),
            total_traffic_used_bytes=int(total_traffic),
            is_blocked=user.is_blocked,
            is_collaborator=user.is_collaborator,
            discount_rules=rules,
        )

    async def list_user_configs(self, user_id: int) -> list[AdminUserConfigItem]:
        rows = (
            self._session.query(OpenVpnClientCredentialORM, SubscriptionORM)
            .outerjoin(
                SubscriptionORM,
                OpenVpnClientCredentialORM.subscription_id == SubscriptionORM.id,
            )
            .filter(OpenVpnClientCredentialORM.user_id == user_id)
            .order_by(OpenVpnClientCredentialORM.id.desc())
            .all()
        )
        items: list[AdminUserConfigItem] = []
        for credential, subscription in rows:
            limit_bytes = subscription.traffic_limit_bytes if subscription else 0
            used_bytes = subscription.traffic_used_bytes if subscription else 0
            remaining = max(limit_bytes - used_bytes, 0)
            items.append(
                AdminUserConfigItem(
                    id=credential.id,
                    config_id=credential.common_name,
                    created_at=credential.created_at,
                    expire_at=subscription.expire_at if subscription else None,
                    traffic_limit_bytes=limit_bytes,
                    traffic_used_bytes=used_bytes,
                    remaining_traffic_bytes=remaining,
                    status=_config_status_label(credential.status),
                    subscription_id=credential.subscription_id,
                    service_type=subscription.service_type if subscription else None,
                )
            )
        return items

    async def get_user_config_detail(
        self,
        user_id: int,
        config_id: str,
    ) -> AdminUserConfigDetail | None:
        row = (
            self._session.query(OpenVpnClientCredentialORM, SubscriptionORM)
            .outerjoin(
                SubscriptionORM,
                OpenVpnClientCredentialORM.subscription_id == SubscriptionORM.id,
            )
            .filter(
                OpenVpnClientCredentialORM.user_id == user_id,
                OpenVpnClientCredentialORM.common_name == config_id,
            )
            .first()
        )
        if not row:
            return None
        credential, subscription = row
        limit_bytes = subscription.traffic_limit_bytes if subscription else 0
        used_bytes = subscription.traffic_used_bytes if subscription else 0
        return AdminUserConfigDetail(
            id=credential.id,
            config_id=credential.common_name,
            created_at=credential.created_at,
            expire_at=subscription.expire_at if subscription else None,
            traffic_limit_bytes=limit_bytes,
            traffic_used_bytes=used_bytes,
            remaining_traffic_bytes=max(limit_bytes - used_bytes, 0),
            status=_config_status_label(credential.status),
            subscription_id=credential.subscription_id,
            service_type=subscription.service_type if subscription else None,
            ovpn_content=credential.ovpn_content,
        )

    async def count_active_configs(self, user_id: int) -> int:
        count = (
            self._session.query(func.count(OpenVpnClientCredentialORM.id))
            .filter(
                OpenVpnClientCredentialORM.user_id == user_id,
                OpenVpnClientCredentialORM.status == OpenVpnConfigStatus.active.value,
            )
            .scalar()
            or 0
        )
        return int(count)

    async def list_discount_rules(self, user_id: int) -> list[CollaboratorDiscountRule]:
        rows = (
            self._session.query(CollaboratorDiscountRuleORM)
            .filter(CollaboratorDiscountRuleORM.user_id == user_id)
            .order_by(CollaboratorDiscountRuleORM.service_type)
            .all()
        )
        return [CollaboratorDiscountRule.model_validate(row) for row in rows]

    async def upsert_discount_rule(
        self,
        user_id: int,
        service_type: str,
        discount_percent: int,
    ) -> CollaboratorDiscountRule:
        existing = (
            self._session.query(CollaboratorDiscountRuleORM)
            .filter(
                CollaboratorDiscountRuleORM.user_id == user_id,
                CollaboratorDiscountRuleORM.service_type == service_type,
            )
            .one_or_none()
        )
        if existing:
            existing.discount_percent = discount_percent
            obj = existing
        else:
            obj = CollaboratorDiscountRuleORM(
                user_id=user_id,
                service_type=service_type,
                discount_percent=discount_percent,
            )
            self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return CollaboratorDiscountRule.model_validate(obj)

    async def delete_discount_rules(self, user_id: int) -> int:
        deleted = (
            self._session.query(CollaboratorDiscountRuleORM)
            .filter(CollaboratorDiscountRuleORM.user_id == user_id)
            .delete()
        )
        self._session.commit()
        return int(deleted or 0)

    async def delete_discount_rule(self, user_id: int, service_type: str) -> bool:
        deleted = (
            self._session.query(CollaboratorDiscountRuleORM)
            .filter(
                CollaboratorDiscountRuleORM.user_id == user_id,
                CollaboratorDiscountRuleORM.service_type == service_type,
            )
            .delete()
        )
        self._session.commit()
        return bool(deleted)

    async def create_audit_log(self, entry: AdminAuditLogEntry) -> AdminAuditLogEntry:
        obj = AdminAuditLogORM(
            admin_telegram_id=entry.admin_telegram_id,
            action=entry.action,
            target_user_id=entry.target_user_id,
            target_config_id=entry.target_config_id,
            details=entry.details,
        )
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return AdminAuditLogEntry.model_validate(obj)

    async def get_discount_percent(self, user_id: int, service_type: str) -> int | None:
        row = (
            self._session.query(CollaboratorDiscountRuleORM.discount_percent)
            .filter(
                CollaboratorDiscountRuleORM.user_id == user_id,
                CollaboratorDiscountRuleORM.service_type == service_type,
            )
            .one_or_none()
        )
        return int(row[0]) if row else None
