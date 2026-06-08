from abc import ABC, abstractmethod

from vpn_core.openvpn_sync.domain.openvpn_user import OpenVpnUser
from vpn_core.server_management_domain.domain.server import Server


class OpenVpnClient(ABC):
    @abstractmethod
    async def health_check(self, server: Server) -> bool:
        pass

    @abstractmethod
    async def create_user(self, server: Server, user: OpenVpnUser) -> str:
        """Create OpenVPN user on node; returns .ovpn config content."""
        pass

    @abstractmethod
    async def delete_user(self, server: Server, common_name: str) -> None:
        pass

    @abstractmethod
    async def apply_endpoint(self, server: Server, *, port: int, proto: str) -> dict:
        """Apply OpenVPN listen port/protocol on the node host."""
        pass

    @abstractmethod
    async def fetch_client_traffic(self, server: Server) -> dict[str, int]:
        """Return current session bytes (received + sent) keyed by common_name."""
        pass
