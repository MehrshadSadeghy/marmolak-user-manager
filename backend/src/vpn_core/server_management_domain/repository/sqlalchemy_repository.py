from sqlalchemy.orm import Session

from vpn_core.server_management_domain.db_model.server import ServerORM
from vpn_core.server_management_domain.domain.queries import GetServerQuery, ListServersQuery
from vpn_core.server_management_domain.domain.server import Server
from vpn_core.server_management_domain.repository.base import ServerRepository
from vpn_core.server_management_domain.repository.mappers import (
    apply_domain_to_orm,
    server_orm_to_domain,
)


class ServerDBRepository(ServerRepository):
    def __init__(self, session: Session):
        self._session = session

    async def create_server(self, server: Server) -> Server:
        obj = ServerORM()
        apply_domain_to_orm(server, obj)
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return server_orm_to_domain(obj)

    async def get_server(self, query: GetServerQuery) -> Server | None:
        obj = self._session.get(ServerORM, query.server_id)
        if not obj:
            return None
        return server_orm_to_domain(obj)

    async def list_servers(self, query: ListServersQuery) -> list[Server]:
        db_query = self._session.query(ServerORM)

        if query.country_code is not None:
            db_query = db_query.filter(
                ServerORM.country_code == query.country_code.upper()
            )
        if query.is_active is not None:
            db_query = db_query.filter(ServerORM.is_active == query.is_active)
        if query.status is not None:
            db_query = db_query.filter(ServerORM.status == query.status)
        if query.openvpn_enabled is not None:
            db_query = db_query.filter(ServerORM.openvpn_enabled == query.openvpn_enabled)
        if query.v2ray_enabled is not None:
            db_query = db_query.filter(ServerORM.v2ray_enabled == query.v2ray_enabled)

        rows = db_query.order_by(ServerORM.country_code, ServerORM.name).all()
        return [server_orm_to_domain(row) for row in rows]

    async def update_server(self, server: Server) -> Server | None:
        obj = self._session.get(ServerORM, server.id)
        if not obj:
            return None

        apply_domain_to_orm(server, obj)
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return server_orm_to_domain(obj)

    async def delete_server(self, query: GetServerQuery) -> bool:
        obj = self._session.get(ServerORM, query.server_id)
        if not obj:
            return False

        self._session.delete(obj)
        self._session.commit()
        return True
