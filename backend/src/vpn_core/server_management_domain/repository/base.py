from abc import ABC, abstractmethod

from vpn_core.server_management_domain.domain.queries import GetServerQuery, ListServersQuery
from vpn_core.server_management_domain.domain.server import Server


class ServerRepository(ABC):
    @abstractmethod
    async def create_server(self, server: Server) -> Server:
        pass

    @abstractmethod
    async def get_server(self, query: GetServerQuery) -> Server | None:
        pass

    @abstractmethod
    async def list_servers(self, query: ListServersQuery) -> list[Server]:
        pass

    @abstractmethod
    async def update_server(self, server: Server) -> Server | None:
        pass

    @abstractmethod
    async def delete_server(self, query: GetServerQuery) -> bool:
        pass
