from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from vpn_core.openvpn_sync.db_model.openvpn_client_credential import OpenVpnClientCredentialORM
from vpn_core.openvpn_sync.db_model.openvpn_traffic_usage import OpenVpnTrafficUsageORM
from vpn_core.openvpn_sync.domain.openvpn_client_credential import (
    OpenVpnClientCredential,
    OpenVpnConfigStatus,
)
from vpn_core.openvpn_sync.domain.openvpn_traffic import OpenVpnTrafficUsage
from vpn_core.openvpn_sync.repository.base import OpenVpnCredentialRepository, OpenVpnTrafficRepository


def _credential_from_orm(obj: OpenVpnClientCredentialORM) -> OpenVpnClientCredential:
    return OpenVpnClientCredential(
        id=obj.id,
        user_id=obj.user_id,
        subscription_id=obj.subscription_id,
        server_id=obj.server_id,
        telegram_id=obj.telegram_id,
        common_name=obj.common_name,
        slot_index=obj.slot_index,
        ovpn_content=obj.ovpn_content,
        status=OpenVpnConfigStatus(obj.status),
        created_at=obj.created_at,
        revoked_at=obj.revoked_at,
    )


class OpenVpnCredentialDBRepository(OpenVpnCredentialRepository):
    def __init__(self, session: Session):
        self._session = session

    async def upsert(self, credential: OpenVpnClientCredential) -> OpenVpnClientCredential:
        existing = (
            self._session.query(OpenVpnClientCredentialORM)
            .filter(
                OpenVpnClientCredentialORM.server_id == credential.server_id,
                OpenVpnClientCredentialORM.common_name == credential.common_name,
            )
            .first()
        )
        if existing:
            existing.ovpn_content = credential.ovpn_content
            existing.status = credential.status.value
            existing.subscription_id = credential.subscription_id
            obj = existing
        else:
            obj = OpenVpnClientCredentialORM(
                user_id=credential.user_id,
                subscription_id=credential.subscription_id,
                server_id=credential.server_id,
                telegram_id=credential.telegram_id,
                common_name=credential.common_name,
                slot_index=credential.slot_index,
                ovpn_content=credential.ovpn_content,
                status=credential.status.value,
            )
            self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return _credential_from_orm(obj)

    async def get_by_common_name(
        self, server_id: int, common_name: str
    ) -> OpenVpnClientCredential | None:
        obj = (
            self._session.query(OpenVpnClientCredentialORM)
            .filter(
                OpenVpnClientCredentialORM.server_id == server_id,
                OpenVpnClientCredentialORM.common_name == common_name,
            )
            .first()
        )
        return _credential_from_orm(obj) if obj else None

    async def get_by_common_name_for_user(
        self,
        config_id: str,
        user_id: int,
    ) -> OpenVpnClientCredential | None:
        obj = (
            self._session.query(OpenVpnClientCredentialORM)
            .filter(
                OpenVpnClientCredentialORM.common_name == config_id,
                OpenVpnClientCredentialORM.user_id == user_id,
            )
            .first()
        )
        return _credential_from_orm(obj) if obj else None

    async def list_by_subscription(
        self,
        subscription_id: int,
        *,
        user_id: int | None = None,
        status: OpenVpnConfigStatus | None = None,
    ) -> list[OpenVpnClientCredential]:
        q = self._session.query(OpenVpnClientCredentialORM).filter(
            OpenVpnClientCredentialORM.subscription_id == subscription_id
        )
        if user_id is not None:
            q = q.filter(OpenVpnClientCredentialORM.user_id == user_id)
        if status is not None:
            q = q.filter(OpenVpnClientCredentialORM.status == status.value)
        rows = q.order_by(OpenVpnClientCredentialORM.id.desc()).all()
        return [_credential_from_orm(row) for row in rows]

    async def list_by_user(
        self,
        user_id: int,
        *,
        status: OpenVpnConfigStatus | None = None,
        server_id: int | None = None,
    ) -> list[OpenVpnClientCredential]:
        q = self._session.query(OpenVpnClientCredentialORM).filter(
            OpenVpnClientCredentialORM.user_id == user_id
        )
        if status is not None:
            q = q.filter(OpenVpnClientCredentialORM.status == status.value)
        if server_id is not None:
            q = q.filter(OpenVpnClientCredentialORM.server_id == server_id)
        rows = q.order_by(OpenVpnClientCredentialORM.server_id, OpenVpnClientCredentialORM.slot_index).all()
        return [_credential_from_orm(r) for r in rows]

    async def get_by_id(self, credential_id: int) -> OpenVpnClientCredential | None:
        obj = self._session.get(OpenVpnClientCredentialORM, credential_id)
        return _credential_from_orm(obj) if obj else None

    async def revoke(self, credential_id: int) -> OpenVpnClientCredential | None:
        obj = self._session.get(OpenVpnClientCredentialORM, credential_id)
        if not obj:
            return None
        obj.status = OpenVpnConfigStatus.revoked.value
        obj.revoked_at = datetime.now(UTC)
        self._session.commit()
        self._session.refresh(obj)
        return _credential_from_orm(obj)


class OpenVpnTrafficDBRepository(OpenVpnTrafficRepository):
    def __init__(self, session: Session):
        self._session = session

    async def add_usage(self, usage: OpenVpnTrafficUsage) -> OpenVpnTrafficUsage:
        obj = OpenVpnTrafficUsageORM(
            user_id=usage.user_id,
            subscription_id=usage.subscription_id,
            bytes_used=usage.bytes_used,
        )
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return OpenVpnTrafficUsage.model_validate(obj)

    async def total_bytes_for_user(self, user_id: int, subscription_id: int | None = None) -> int:
        q = self._session.query(func.coalesce(func.sum(OpenVpnTrafficUsageORM.bytes_used), 0)).filter(
            OpenVpnTrafficUsageORM.user_id == user_id
        )
        if subscription_id is not None:
            q = q.filter(OpenVpnTrafficUsageORM.subscription_id == subscription_id)
        total = q.scalar()
        return int(total or 0)
