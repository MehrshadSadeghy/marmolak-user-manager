from dataclasses import dataclass

from fastapi import HTTPException

from vpn_core.server_management_domain.domain.queries import GetServerQuery
from vpn_core.server_management_domain.domain.server import Server
from vpn_core.server_management_domain.service import ServerService
from vpn_core.v2ray_sync.repository.base import V2RayCredentialRepository


@dataclass(frozen=True)
class ServerCapacitySnapshot:
    max_users: int
    current_users: int
    is_full: bool
    remaining_slots: int


class V2RayCapacityService:
    def __init__(
        self,
        *,
        credential_repository: V2RayCredentialRepository,
        server_service: ServerService,
    ):
        self._credential_repository = credential_repository
        self._server_service = server_service

    async def count_active_configs(self, server_id: int) -> int:
        return await self._credential_repository.count_active_by_server(server_id)

    async def get_server_capacity_snapshot(self, server: Server) -> ServerCapacitySnapshot:
        if server.id is None:
            raise ValueError("Server id is required")
        current_users = await self.count_active_configs(server.id)
        max_users = server.capacity.max_users
        return ServerCapacitySnapshot(
            max_users=max_users,
            current_users=current_users,
            is_full=current_users >= max_users,
            remaining_slots=max(0, max_users - current_users),
        )

    async def sync_current_users(self, server_id: int) -> None:
        server = await self._server_service.get_server(GetServerQuery(server_id=server_id))
        if not server:
            return
        server.capacity.current_users = await self.count_active_configs(server_id)
        await self._server_service.update_server(server)

    async def assert_server_has_capacity(self, server_id: int) -> None:
        server = await self._server_service.get_server(GetServerQuery(server_id=server_id))
        if not server or not server.is_active:
            raise HTTPException(status_code=404, detail="Server not found or inactive")
        snapshot = await self.get_server_capacity_snapshot(server)
        if snapshot.is_full:
            raise HTTPException(status_code=400, detail="Server is at full capacity")
