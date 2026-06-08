from abc import ABC, abstractmethod

from vpn_core.openvpn_sync.domain.openvpn_client_credential import (
    OpenVpnClientCredential,
    OpenVpnConfigStatus,
)
from vpn_core.openvpn_sync.domain.openvpn_traffic import OpenVpnTrafficUsage


class OpenVpnCredentialRepository(ABC):
    @abstractmethod
    async def upsert(self, credential: OpenVpnClientCredential) -> OpenVpnClientCredential:
        pass

    @abstractmethod
    async def get_by_common_name(
        self, server_id: int, common_name: str
    ) -> OpenVpnClientCredential | None:
        pass

    @abstractmethod
    async def get_by_common_name_for_user(
        self,
        config_id: str,
        user_id: int,
    ) -> OpenVpnClientCredential | None:
        pass

    @abstractmethod
    async def list_by_subscription(
        self,
        subscription_id: int,
        *,
        user_id: int | None = None,
        status: OpenVpnConfigStatus | None = None,
    ) -> list[OpenVpnClientCredential]:
        pass

    @abstractmethod
    async def list_by_user(
        self,
        user_id: int,
        *,
        status: OpenVpnConfigStatus | None = None,
        server_id: int | None = None,
    ) -> list[OpenVpnClientCredential]:
        pass

    @abstractmethod
    async def get_by_id(self, credential_id: int) -> OpenVpnClientCredential | None:
        pass

    @abstractmethod
    async def revoke(self, credential_id: int) -> OpenVpnClientCredential | None:
        pass

    @abstractmethod
    async def set_status(
        self,
        credential_id: int,
        status: OpenVpnConfigStatus,
    ) -> OpenVpnClientCredential | None:
        pass


class OpenVpnTrafficRepository(ABC):
    @abstractmethod
    async def add_usage(self, usage: OpenVpnTrafficUsage) -> OpenVpnTrafficUsage:
        pass

    @abstractmethod
    async def total_bytes_for_user(self, user_id: int, subscription_id: int | None = None) -> int:
        pass
