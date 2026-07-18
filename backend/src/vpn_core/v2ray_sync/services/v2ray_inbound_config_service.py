import logging

from fastapi import HTTPException

from vpn_core.server_management_domain.domain.queries import GetServerQuery
from vpn_core.server_management_domain.service import ServerService
from vpn_core.v2ray_sync.client.factory import V2RayClientFactory
from vpn_core.v2ray_sync.services.helpers import node_api_configured

LOGGER = logging.getLogger(__name__)


class V2RayInboundConfigService:
    """Reads and applies v2ray-node inbound settings, then syncs user-manager server record."""

    def __init__(self, *, server_service: ServerService):
        self._server_service = server_service
        self._client = V2RayClientFactory.create()

    async def _get_server(self, server_id: int):
        server = await self._server_service.get_server(GetServerQuery(server_id=server_id))
        if not server or not server.is_active:
            raise HTTPException(status_code=404, detail="Server not found or inactive")
        if not node_api_configured(server):
            raise HTTPException(status_code=400, detail="Server does not support V2Ray")
        if not server.xray_inbound_tag:
            raise HTTPException(status_code=400, detail="Server is missing xray_inbound_tag")
        return server

    async def get_inbound_config(self, server_id: int) -> dict:
        server = await self._get_server(server_id)
        config = await self._client.get_inbound_config(server)
        return {
            "server_id": server_id,
            "server_name": server.name,
            **config,
        }

    async def apply_inbound_config(
        self,
        server_id: int,
        payload: dict,
        *,
        partial: bool = False,
    ) -> dict:
        server = await self._get_server(server_id)
        previous = await self._client.get_inbound_config(server)
        if partial:
            result = await self._client.patch_inbound_config(server, payload)
        else:
            merged = {**previous, **payload}
            merged["inbound_tag"] = payload.get("inbound_tag") or previous.get("inbound_tag") or server.xray_inbound_tag
            merged["server_host"] = payload.get("server_host") or previous.get("server_host") or server.v2ray.vpn_host or server.connection.host
            result = await self._client.apply_inbound_config(server, merged)

        server.v2ray.vpn_port = int(result.get("port") or server.v2ray.vpn_port)
        server.v2ray.network = str(result.get("network") or server.v2ray.network)
        server.v2ray.security = str(result.get("security") or server.v2ray.security)
        server.v2ray.ws_path = str(result.get("ws_path") or server.v2ray.ws_path)
        if host := result.get("server_host"):
            server.v2ray.vpn_host = str(host)
        if server.xray_inbound_tag != result.get("inbound_tag") and result.get("inbound_tag"):
            server.xray_inbound_tag = str(result["inbound_tag"])

        updated = await self._server_service.update_server(server)
        if not updated:
            raise HTTPException(status_code=404, detail="Server not found")

        LOGGER.info(
            "V2Ray inbound updated for server %s: %s/%s %s+%s",
            server_id,
            result.get("protocol"),
            result.get("port"),
            result.get("network"),
            result.get("security"),
        )
        return {
            "server_id": server_id,
            "server_name": updated.name,
            "previous": previous,
            **result,
        }
