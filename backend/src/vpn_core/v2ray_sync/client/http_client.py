import hashlib
import hmac
import json
import logging
import time

import httpx

from vpn_core.server_management_domain.domain.server import Server
from vpn_core.v2ray_sync.client.base import V2RayClient
from vpn_core.v2ray_sync.domain.traffic_snapshot import V2RayTrafficSnapshot
from vpn_core.v2ray_sync.domain.v2ray_user import V2RayUser

LOGGER = logging.getLogger(__name__)


class HttpV2RayClient(V2RayClient):
    """Calls v2ray-node HTTP API with HMAC signing."""

    def __init__(self, timeout: float = 30.0):
        self._timeout = timeout

    def _node_base_url(self, server: Server) -> str:
        host = server.connection.host
        port = server.v2ray.node_api_port
        return f"http://{host}:{port}"

    def _secret(self, server: Server) -> str:
        secret = server.v2ray.node_api_secret
        if not secret:
            raise ValueError(f"Server {server.id} has no v2ray node_api_secret configured")
        return secret

    def _sign(self, secret: str, timestamp: str, method: str, path: str, body: bytes) -> str:
        message = f"{timestamp}{method.upper()}{path}".encode() + body
        return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()

    async def _request(
        self,
        server: Server,
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> dict:
        if method.upper() == "GET":
            body = b""
        else:
            body = json.dumps(payload or {}, separators=(",", ":")).encode()
        timestamp = str(int(time.time()))
        secret = self._secret(server)
        signature = self._sign(secret, timestamp, method, path, body)
        headers = {
            "Content-Type": "application/json",
            "X-Node-Timestamp": timestamp,
            "X-Node-Signature": signature,
        }
        url = f"{self._node_base_url(server)}{path}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers)
            else:
                response = await client.request(method, url, content=body, headers=headers)
            if response.is_error:
                LOGGER.error(
                    "V2Ray node request failed %s %s -> %s: %s",
                    method,
                    url,
                    response.status_code,
                    response.text,
                )
            response.raise_for_status()
            return response.json()

    def _vpn_remote(self, server: Server) -> dict:
        host = server.v2ray.vpn_host or server.connection.host
        return {
            "server_host": host,
            "server_port": server.v2ray.vpn_port,
            "ws_path": server.v2ray.ws_path,
            "network": server.v2ray.network,
            "security": server.v2ray.security,
            "sni": server.v2ray.sni,
            "fingerprint": server.v2ray.fingerprint,
        }

    async def health_check(self, server: Server) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{self._node_base_url(server)}/node/health")
                response.raise_for_status()
                return response.json().get("status") == "healthy"
        except Exception as exc:
            LOGGER.warning("V2Ray node health check failed for server %s: %s", server.id, exc)
            return False

    async def create_user(self, server: Server, user: V2RayUser) -> tuple[str, str]:
        payload = {
            "email": user.email,
            "server_config": self._vpn_remote(server),
        }
        data = await self._request(server, "POST", "/node/vpn/v2ray/create", payload)
        vless_link = data.get("vless_link")
        client_uuid = data.get("client_uuid")
        if not vless_link or not client_uuid:
            raise RuntimeError("Node did not return vless_link/client_uuid")
        return vless_link, client_uuid

    async def delete_user(self, server: Server, email: str) -> None:
        await self._request(server, "POST", "/node/vpn/v2ray/delete", {"email": email})

    async def fetch_client_traffic(self, server: Server) -> V2RayTrafficSnapshot:
        data = await self._request(server, "GET", "/node/vpn/v2ray/traffic")
        clients = data.get("clients") or []
        return V2RayTrafficSnapshot(
            live={
                str(item["email"]): int(item["bytes_total"])
                for item in clients
                if item.get("email") is not None
            }
        )

    async def get_inbound_config(self, server: Server) -> dict:
        return await self._request(server, "GET", "/node/vpn/v2ray/inbound-config")

    async def apply_inbound_config(self, server: Server, payload: dict) -> dict:
        body = {**payload}
        body.setdefault("inbound_tag", server.xray_inbound_tag)
        body.setdefault("server_host", server.v2ray.vpn_host or server.connection.host)
        return await self._request(server, "PUT", "/node/vpn/v2ray/inbound-config", body)

    async def patch_inbound_config(self, server: Server, payload: dict) -> dict:
        return await self._request(server, "PATCH", "/node/vpn/v2ray/inbound-config", payload)
