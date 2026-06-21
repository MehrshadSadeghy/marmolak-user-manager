from __future__ import annotations

from typing import Any

import httpx


class PasarguardPanelClient:
    def __init__(self, panel_base_url: str, subscription_path: str = "sub"):
        self._panel_base_url = panel_base_url.rstrip("/")
        self._subscription_path = subscription_path.strip("/")

    def subscription_url(self, token: str) -> str:
        return f"{self._panel_base_url}/{self._subscription_path}/{token}"

    async def get_subscription_info(self, token: str) -> dict[str, Any]:
        url = f"{self._panel_base_url}/{self._subscription_path}/{token}/info"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    async def get_subscription_apps(self, token: str) -> list[dict[str, Any]]:
        url = f"{self._panel_base_url}/{self._subscription_path}/{token}/apps"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
            return payload if isinstance(payload, list) else []
