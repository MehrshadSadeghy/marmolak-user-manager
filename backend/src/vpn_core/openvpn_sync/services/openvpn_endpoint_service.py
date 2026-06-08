import logging

from fastapi import HTTPException

from vpn_core.openvpn_sync.client.factory import OpenVpnClientFactory
from vpn_core.openvpn_sync.services.helpers import node_api_configured
from vpn_core.server_management_domain.domain.queries import GetServerQuery
from vpn_core.server_management_domain.service import ServerService

LOGGER = logging.getLogger(__name__)


class OpenVpnEndpointService:
    """Updates OpenVPN port/protocol on the node and in user-manager."""

    def __init__(self, *, server_service: ServerService):
        self._server_service = server_service
        self._client = OpenVpnClientFactory.create()

    async def apply_endpoint(self, server_id: int, port: int, proto: str) -> dict:
        proto = proto.lower()
        if proto not in ("udp", "tcp"):
            raise HTTPException(status_code=400, detail="proto must be udp or tcp")

        server = await self._server_service.get_server(GetServerQuery(server_id=server_id))
        if not server or not server.is_active:
            raise HTTPException(status_code=404, detail="Server not found or inactive")
        if not node_api_configured(server):
            raise HTTPException(status_code=400, detail="Server does not support OpenVPN")

        previous_port = server.openvpn.vpn_port
        previous_proto = server.openvpn.vpn_proto

        node_result = await self._client.apply_endpoint(server, port=port, proto=proto)

        server.openvpn.vpn_port = port
        server.openvpn.vpn_proto = proto
        updated = await self._server_service.update_server(server)
        if not updated:
            raise HTTPException(status_code=404, detail="Server not found")

        LOGGER.info(
            "OpenVPN endpoint updated for server %s: %s/%s -> %s/%s",
            server_id,
            previous_proto,
            previous_port,
            proto,
            port,
        )

        return {
            "server_id": server_id,
            "server_name": updated.name,
            "port": port,
            "proto": proto,
            "previous_port": previous_port,
            "previous_proto": previous_proto,
            **node_result,
        }

    async def list_openvpn_servers(self):
        from vpn_core.server_management_domain.domain.queries import ListServersQuery

        return await self._server_service.list_servers(
            ListServersQuery(openvpn_enabled=True, is_active=True)
        )
