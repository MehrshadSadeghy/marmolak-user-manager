from abc import ABC, abstractmethod

from vpn_core.v2ray_sync.domain.traffic_snapshot import V2RayTrafficSnapshot
from vpn_core.v2ray_sync.domain.v2ray_user import V2RayUser
from vpn_core.server_management_domain.domain.server import Server


class V2RayClient(ABC):
    @abstractmethod
    async def health_check(self, server: Server) -> bool:
        pass

    @abstractmethod
    async def create_user(self, server: Server, user: V2RayUser) -> tuple[str, str]:
        """Return (vless_link, client_uuid)."""

    @abstractmethod
    async def delete_user(self, server: Server, email: str) -> None:
        pass

    @abstractmethod
    async def fetch_client_traffic(self, server: Server) -> V2RayTrafficSnapshot:
        pass

    @abstractmethod
    async def get_inbound_config(self, server: Server) -> dict:
        pass

    @abstractmethod
    async def apply_inbound_config(self, server: Server, payload: dict) -> dict:
        pass

    @abstractmethod
    async def patch_inbound_config(self, server: Server, payload: dict) -> dict:
        pass
