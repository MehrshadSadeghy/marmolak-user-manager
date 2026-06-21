import hashlib
import hmac
import json
import logging
import time

import httpx

from vpn_core.openvpn_sync.client.base import OpenVpnClient
from vpn_core.openvpn_sync.domain.openvpn_user import OpenVpnUser
from vpn_core.server_management_domain.domain.server import Server

LOGGER = logging.getLogger(__name__)


class HttpOpenVpnClient(OpenVpnClient):
    """Calls vpn-node HTTP API with HMAC signing."""

    def __init__(self, timeout: float = 30.0, endpoint_timeout: float = 120.0):
        self._timeout = timeout
        self._endpoint_timeout = endpoint_timeout

    def _node_base_url(self, server: Server) -> str:
        host = server.connection.host
        port = server.connection.api_port
        return f"http://{host}:{port}"

    def _secret(self, server: Server) -> str:
        secret = server.openvpn.node_api_secret
        if not secret:
            raise ValueError(f"Server {server.id} has no node_api_secret configured")
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
        timeout = self._endpoint_timeout if path.endswith("/apply-endpoint") else self._timeout
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, content=body, headers=headers)
            if response.is_error:
                LOGGER.error(
                    "OpenVPN node request failed %s %s -> %s: %s",
                    method,
                    url,
                    response.status_code,
                    response.text,
                )
            response.raise_for_status()
            return response.json()

    def _vpn_remote(self, server: Server) -> tuple[str, int, str]:
        host = server.openvpn.vpn_host or server.connection.host
        return host, server.openvpn.vpn_port, server.openvpn.vpn_proto

    async def health_check(self, server: Server) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{self._node_base_url(server)}/node/health")
                response.raise_for_status()
                return response.json().get("status") == "healthy"
        except Exception as exc:
            LOGGER.warning("OpenVPN node health check failed for server %s: %s", server.id, exc)
            return False

    async def create_user(
        self,
        server: Server,
        user: OpenVpnUser,
        *,
        auth_mode: str | None = None,
    ) -> str:
        host, port, proto = self._vpn_remote(server)
        payload: dict = {
            "common_name": user.common_name,
            "server_config": {
                "server_host": host,
                "server_port": port,
                "proto": proto,
            },
        }
        if auth_mode:
            payload["auth_mode"] = auth_mode
        data = await self._request(
            server,
            "POST",
            "/node/vpn/openvpn/create",
            payload,
        )
        ovpn = data.get("ovpn_config")
        if not ovpn:
            raise RuntimeError("Node did not return ovpn_config")
        return ovpn

    async def create_auth_user(self, server: Server, username: str, password_hash: str) -> dict:
        return await self._request(
            server,
            "POST",
            "/node/vpn/openvpn/auth/create",
            {"username": username, "password_hash": password_hash},
        )

    async def rotate_auth_user(self, server: Server, username: str, password_hash: str) -> dict:
        return await self._request(
            server,
            "POST",
            "/node/vpn/openvpn/auth/rotate",
            {"username": username, "password_hash": password_hash},
        )

    async def delete_auth_user(self, server: Server, username: str) -> None:
        await self._request(
            server,
            "POST",
            "/node/vpn/openvpn/auth/delete",
            {"username": username},
        )

    async def apply_auth_mode(self, server: Server, auth_mode: str) -> dict:
        return await self._request(
            server,
            "POST",
            "/node/vpn/openvpn/apply-auth-mode",
            {"auth_mode": auth_mode},
        )

    async def delete_user(self, server: Server, common_name: str) -> None:
        await self._request(
            server,
            "POST",
            "/node/vpn/openvpn/delete",
            {"common_name": common_name},
        )

    async def apply_endpoint(self, server: Server, *, port: int, proto: str) -> dict:
        return await self._request(
            server,
            "POST",
            "/node/vpn/openvpn/apply-endpoint",
            {"port": port, "proto": proto},
        )

    async def fetch_client_traffic(self, server: Server) -> dict[str, int]:
        data = await self._request(server, "GET", "/node/vpn/openvpn/traffic")
        clients = data.get("clients") or []
        return {
            str(item["common_name"]): int(item["bytes_total"])
            for item in clients
            if item.get("common_name") is not None
        }
