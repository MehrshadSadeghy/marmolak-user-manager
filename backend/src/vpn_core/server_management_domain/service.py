from vpn_core.server_management_domain.domain.commands import (
    UpdateResourceMonitoringCommand,
    UpdateServerStatusCommand,
)
from vpn_core.server_management_domain.domain.queries import (
    GetServerQuery,
    ListServersQuery,
)
from vpn_core.server_management_domain.domain.server import Server
from vpn_core.server_management_domain.repository.base import ServerRepository


class ServerService:
    def __init__(self, repository: ServerRepository):
        self._repository = repository

    async def create_server(self, server: Server) -> Server:
        server.country_code = server.country_code.upper()
        return await self._repository.create_server(server)

    async def get_server(self, query: GetServerQuery) -> Server | None:
        return await self._repository.get_server(query)

    async def list_servers(self, query: ListServersQuery) -> list[Server]:
        if query.country_code is not None:
            query.country_code = query.country_code.upper()
        return await self._repository.list_servers(query)

    async def update_server(self, server: Server) -> Server | None:
        if server.id is None:
            return None

        server.country_code = server.country_code.upper()
        return await self._repository.update_server(server)

    async def update_server_status(self, command: UpdateServerStatusCommand) -> Server | None:
        server = await self._repository.get_server(
            GetServerQuery(server_id=command.server_id)
        )
        if not server:
            return None

        server.status = command.status
        return await self._repository.update_server(server)

    async def update_resource_monitoring(
        self,
        command: UpdateResourceMonitoringCommand,
    ) -> Server | None:
        server = await self._repository.get_server(
            GetServerQuery(server_id=command.server_id)
        )
        if not server:
            return None

        server.monitoring = command.monitoring
        return await self._repository.update_server(server)

    async def delete_server(self, query: GetServerQuery) -> bool:
        return await self._repository.delete_server(query)
