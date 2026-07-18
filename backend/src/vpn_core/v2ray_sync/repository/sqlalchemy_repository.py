from datetime import UTC, datetime

from sqlalchemy.orm import Session

from vpn_core.v2ray_sync.db_model.v2ray_client_credential import V2RayClientCredentialORM
from vpn_core.v2ray_sync.domain.v2ray_client_credential import (
    V2RayClientCredential,
    V2RayConfigStatus,
)
from vpn_core.v2ray_sync.repository.base import V2RayCredentialRepository


def _credential_from_orm(obj: V2RayClientCredentialORM) -> V2RayClientCredential:
    return V2RayClientCredential(
        id=obj.id,
        user_id=obj.user_id,
        subscription_id=obj.subscription_id,
        server_id=obj.server_id,
        telegram_id=obj.telegram_id,
        email=obj.email,
        client_uuid=obj.client_uuid,
        slot_index=obj.slot_index,
        vless_link=obj.vless_link,
        status=V2RayConfigStatus(obj.status),
        last_status_bytes=obj.last_status_bytes,
        created_at=obj.created_at,
        revoked_at=obj.revoked_at,
    )


class V2RayCredentialDBRepository(V2RayCredentialRepository):
    def __init__(self, session: Session):
        self._session = session

    async def upsert(self, credential: V2RayClientCredential) -> V2RayClientCredential:
        existing = (
            self._session.query(V2RayClientCredentialORM)
            .filter(
                V2RayClientCredentialORM.server_id == credential.server_id,
                V2RayClientCredentialORM.email == credential.email,
            )
            .first()
        )
        if existing:
            existing.vless_link = credential.vless_link
            existing.client_uuid = credential.client_uuid
            existing.status = credential.status.value
            existing.subscription_id = credential.subscription_id
            existing.last_status_bytes = credential.last_status_bytes
            existing.revoked_at = credential.revoked_at
            obj = existing
        else:
            obj = V2RayClientCredentialORM(
                user_id=credential.user_id,
                subscription_id=credential.subscription_id,
                server_id=credential.server_id,
                telegram_id=credential.telegram_id,
                email=credential.email,
                client_uuid=credential.client_uuid,
                slot_index=credential.slot_index,
                vless_link=credential.vless_link,
                status=credential.status.value,
                last_status_bytes=credential.last_status_bytes,
            )
            self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return _credential_from_orm(obj)

    async def get_by_email(self, server_id: int, email: str) -> V2RayClientCredential | None:
        obj = (
            self._session.query(V2RayClientCredentialORM)
            .filter(
                V2RayClientCredentialORM.server_id == server_id,
                V2RayClientCredentialORM.email == email,
            )
            .first()
        )
        return _credential_from_orm(obj) if obj else None

    async def get_by_email_for_user(self, email: str, user_id: int) -> V2RayClientCredential | None:
        obj = (
            self._session.query(V2RayClientCredentialORM)
            .filter(
                V2RayClientCredentialORM.email == email,
                V2RayClientCredentialORM.user_id == user_id,
            )
            .first()
        )
        return _credential_from_orm(obj) if obj else None

    async def list_by_user(
        self,
        user_id: int,
        *,
        status: V2RayConfigStatus | None = None,
        server_id: int | None = None,
    ) -> list[V2RayClientCredential]:
        query = self._session.query(V2RayClientCredentialORM).filter(
            V2RayClientCredentialORM.user_id == user_id
        )
        if status is not None:
            query = query.filter(V2RayClientCredentialORM.status == status.value)
        if server_id is not None:
            query = query.filter(V2RayClientCredentialORM.server_id == server_id)
        return [_credential_from_orm(obj) for obj in query.all()]

    async def list_by_subscription(
        self,
        subscription_id: int,
        *,
        user_id: int | None = None,
        status: V2RayConfigStatus | None = None,
    ) -> list[V2RayClientCredential]:
        query = self._session.query(V2RayClientCredentialORM).filter(
            V2RayClientCredentialORM.subscription_id == subscription_id
        )
        if user_id is not None:
            query = query.filter(V2RayClientCredentialORM.user_id == user_id)
        if status is not None:
            query = query.filter(V2RayClientCredentialORM.status == status.value)
        return [_credential_from_orm(obj) for obj in query.all()]

    async def count_active_by_server(self, server_id: int) -> int:
        return (
            self._session.query(V2RayClientCredentialORM)
            .filter(
                V2RayClientCredentialORM.server_id == server_id,
                V2RayClientCredentialORM.status == V2RayConfigStatus.active.value,
            )
            .count()
        )

    async def revoke(self, credential: V2RayClientCredential) -> V2RayClientCredential:
        obj = self._session.query(V2RayClientCredentialORM).filter_by(id=credential.id).first()
        if not obj:
            return credential
        obj.status = V2RayConfigStatus.revoked.value
        obj.revoked_at = datetime.now(UTC)
        self._session.commit()
        self._session.refresh(obj)
        return _credential_from_orm(obj)
