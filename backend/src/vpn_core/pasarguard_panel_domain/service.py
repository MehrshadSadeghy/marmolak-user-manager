from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import HTTPException

from vpn_core.pasarguard_panel_domain.client.http_client import PasarguardPanelClient
from vpn_core.pasarguard_panel_domain.domain.panel_link import PasarguardPanelLink
from vpn_core.pasarguard_panel_domain.repository.base import PasarguardPanelLinkRepository
from vpn_core.pasarguard_panel_domain.utils.token import parse_subscription_token


@dataclass(frozen=True)
class PasarguardPanelConfig:
    panel_base_url: str
    subscription_path: str
    webapp_url: str | None

    @property
    def enabled(self) -> bool:
        return bool(self.panel_base_url)


def get_pasarguard_panel_config() -> PasarguardPanelConfig:
    panel_base_url = os.getenv("PASARGUARD_PANEL_URL", "").strip().rstrip("/")
    subscription_path = os.getenv("PASARGUARD_SUBSCRIPTION_PATH", "sub").strip().strip("/") or "sub"
    webapp_url = os.getenv("PASARGUARD_PANEL_WEBAPP_URL", "").strip().rstrip("/") or None
    if webapp_url is None and panel_base_url.startswith("https://"):
        webapp_url = panel_base_url
    return PasarguardPanelConfig(
        panel_base_url=panel_base_url,
        subscription_path=subscription_path,
        webapp_url=webapp_url,
    )


class PasarguardPanelService:
    def __init__(
        self,
        *,
        repository: PasarguardPanelLinkRepository,
        config: PasarguardPanelConfig | None = None,
    ):
        self._repository = repository
        self._config = config or get_pasarguard_panel_config()

    def get_panel_settings(self) -> dict[str, Any]:
        return {
            "enabled": self._config.enabled,
            "panel_base_url": self._config.panel_base_url or None,
            "subscription_path": self._config.subscription_path,
            "webapp_url": self._config.webapp_url,
        }

    def _client(self) -> PasarguardPanelClient:
        if not self._config.enabled:
            raise HTTPException(status_code=503, detail="PasarGuard panel integration is not configured")
        return PasarguardPanelClient(
            panel_base_url=self._config.panel_base_url,
            subscription_path=self._config.subscription_path,
        )

    async def connect_user_panel(self, user_id: int, subscription_input: str) -> dict[str, Any]:
        token = parse_subscription_token(subscription_input)
        if not token:
            raise HTTPException(status_code=400, detail="Invalid subscription link or token")

        client = self._client()
        try:
            info = await client.get_subscription_info(token)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise HTTPException(status_code=404, detail="PasarGuard subscription not found") from exc
            raise HTTPException(
                status_code=502,
                detail=f"PasarGuard panel request failed ({exc.response.status_code})",
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail="Could not reach PasarGuard panel") from exc

        username = str(info.get("username") or token)
        subscription_url = client.subscription_url(token)
        link = await self._repository.upsert(
            PasarguardPanelLink(
                user_id=user_id,
                subscription_token=token,
                panel_username=username,
                subscription_url=subscription_url,
            )
        )
        return {
            "link": link,
            "info": self._format_subscription_info(info, subscription_url),
            "apps": await self._fetch_apps(client, token, subscription_url),
        }

    async def get_user_connection(self, user_id: int) -> dict[str, Any] | None:
        link = await self._repository.get_by_user_id(user_id)
        if not link:
            return None
        client = self._client()
        try:
            info = await client.get_subscription_info(link.subscription_token)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return {
                    "link": link,
                    "info": None,
                    "apps": [],
                    "error": "PasarGuard subscription not found",
                }
            raise HTTPException(
                status_code=502,
                detail=f"PasarGuard panel request failed ({exc.response.status_code})",
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail="Could not reach PasarGuard panel") from exc

        return {
            "link": link,
            "info": self._format_subscription_info(info, link.subscription_url),
            "apps": await self._fetch_apps(client, link.subscription_token, link.subscription_url),
        }

    async def _fetch_apps(
        self,
        client: PasarguardPanelClient,
        token: str,
        subscription_url: str,
    ) -> list[dict[str, Any]]:
        try:
            apps = await client.get_subscription_apps(token)
        except httpx.HTTPError:
            return []
        return self._format_apps(apps, subscription_url)

    @staticmethod
    def _format_apps(apps: list[dict[str, Any]], subscription_url: str) -> list[dict[str, Any]]:
        encoded_url = httpx.URL(subscription_url)
        safe_url = str(encoded_url)
        formatted: list[dict[str, Any]] = []
        for app in apps:
            import_url = (app.get("import_url") or "").strip()
            if not import_url:
                continue
            formatted.append(
                {
                    "name": app.get("name") or "App",
                    "platform": app.get("platform"),
                    "recommended": bool(app.get("recommended")),
                    "import_url": import_url.format(url=safe_url),
                }
            )
        return formatted

    @staticmethod
    def _format_subscription_info(info: dict[str, Any], subscription_url: str) -> dict[str, Any]:
        expire = info.get("expire")
        expire_label = "∞"
        days_left: int | str = "∞"
        if expire:
            try:
                expire_dt = datetime.fromisoformat(str(expire).replace("Z", "+00:00"))
                expire_label = expire_dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M")
                days_left = max((expire_dt.astimezone(UTC) - datetime.now(UTC)).days, 0)
            except ValueError:
                expire_label = str(expire)

        data_limit = info.get("data_limit") or 0
        used_traffic = info.get("used_traffic") or 0
        return {
            "username": info.get("username"),
            "status": info.get("status"),
            "data_limit_bytes": data_limit,
            "used_traffic_bytes": used_traffic,
            "data_limit_label": PasarguardPanelService._readable_size(data_limit) if data_limit else "∞",
            "used_traffic_label": PasarguardPanelService._readable_size(used_traffic),
            "expire_at": expire_label,
            "days_left": days_left,
            "subscription_url": subscription_url,
        }

    @staticmethod
    def _readable_size(num_bytes: int) -> str:
        if num_bytes >= 1024**3:
            return f"{num_bytes / 1024**3:.2f} GB"
        if num_bytes >= 1024**2:
            return f"{num_bytes / 1024**2:.2f} MB"
        return f"{num_bytes} B"
