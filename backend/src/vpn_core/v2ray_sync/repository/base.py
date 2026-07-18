from abc import ABC, abstractmethod

from vpn_core.v2ray_sync.domain.v2ray_client_credential import (
    V2RayClientCredential,
    V2RayConfigStatus,
)


class V2RayCredentialRepository(ABC):
    @abstractmethod
    async def upsert(self, credential: V2RayClientCredential) -> V2RayClientCredential:
        pass

    @abstractmethod
    async def get_by_email(self, server_id: int, email: str) -> V2RayClientCredential | None:
        pass

    @abstractmethod
    async def get_by_email_for_user(self, email: str, user_id: int) -> V2RayClientCredential | None:
        pass

    @abstractmethod
    async def list_by_user(
        self,
        user_id: int,
        *,
        status: V2RayConfigStatus | None = None,
        server_id: int | None = None,
    ) -> list[V2RayClientCredential]:
        pass

    @abstractmethod
    async def list_by_subscription(
        self,
        subscription_id: int,
        *,
        user_id: int | None = None,
        status: V2RayConfigStatus | None = None,
    ) -> list[V2RayClientCredential]:
        pass

    @abstractmethod
    async def count_active_by_server(self, server_id: int) -> int:
        pass
