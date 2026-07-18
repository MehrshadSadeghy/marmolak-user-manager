from abc import ABC, abstractmethod

from vpn_core.openvpn_sync.domain.openvpn_user import OpenVpnUser
from vpn_core.openvpn_sync.domain.traffic_snapshot import OpenVpnTrafficSnapshot
from vpn_core.server_management_domain.domain.server import Server


class OpenVpnClient(ABC):
    @abstractmethod
    async def health_check(self, server: Server) -> bool:
        pass

    @abstractmethod
    async def create_user(
        self,
        server: Server,
        user: OpenVpnUser,
        *,
        auth_mode: str | None = None,
    ) -> str:
        """Create OpenVPN user on node; returns .ovpn config content."""
        pass

    @abstractmethod
    async def create_auth_user(self, server: Server, username: str, password_hash: str) -> dict:
        """Store username/password hash on node for auth-user-pass verification."""
        pass

    @abstractmethod
    async def rotate_auth_user(self, server: Server, username: str, password_hash: str) -> dict:
        pass

    @abstractmethod
    async def delete_auth_user(self, server: Server, username: str) -> None:
        pass

    @abstractmethod
    async def apply_auth_mode(self, server: Server, auth_mode: str) -> dict:
        """Apply OpenVPN server auth mode (certificate/dual/user_pass) on the node host."""
        pass

    @abstractmethod
    async def delete_user(self, server: Server, common_name: str) -> None:
        pass

    @abstractmethod
    async def apply_endpoint(self, server: Server, *, port: int, proto: str) -> dict:
        """Apply OpenVPN listen port/protocol on the node host."""
        pass

    @abstractmethod
    async def fetch_client_traffic(self, server: Server) -> OpenVpnTrafficSnapshot:
        """Return live session bytes and pending disconnect totals keyed by common_name."""
        pass

    @abstractmethod
    async def consume_disconnect_traffic(self, server: Server, common_names: list[str]) -> None:
        """Acknowledge processed disconnect session counters on the node."""
        pass
