from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import HTTPException

from vpn_core.subscription_domain.domain.queries import GetSubscriptionQuery, ListSubscriptionsQuery
from vpn_core.subscription_domain.domain.subscription import SubscriptionStatus
from vpn_core.subscription_domain.service import SubscriptionService
from vpn_core.v2ray_sync.domain.v2ray_client_credential import V2RayConfigStatus
from vpn_core.v2ray_sync.services.v2ray_provisioning_service import V2RayProvisioningService

SUPPORTED_PROXY_SCHEMES = ("vless://", "vmess://", "trojan://", "ss://")


@dataclass(frozen=True)
class ClientSubscriptionConfig:
    base_url: str
    subscription_path: str = "sub"
    profile_title: str = "Marmolak VPN"
    update_interval_hours: int = 6

    @classmethod
    def from_env(cls, base_url: str) -> "ClientSubscriptionConfig":
        path = os.getenv("SUBSCRIPTION_PATH", "sub").strip().strip("/") or "sub"
        title = os.getenv("SUBSCRIPTION_PROFILE_TITLE", "Marmolak VPN").strip() or "Marmolak VPN"
        interval = int(os.getenv("SUBSCRIPTION_UPDATE_INTERVAL_HOURS", "6"))
        return cls(
            base_url=base_url.rstrip("/"),
            subscription_path=path,
            profile_title=title,
            update_interval_hours=interval,
        )

    def build_url(self, token: str) -> str:
        return f"{self.base_url}/{self.subscription_path}/{token}"


@dataclass(frozen=True)
class SubscriptionFeed:
    body: str
    headers: dict[str, str]
    link_count: int


class ClientSubscriptionService:
    """Serves Hiddify/Happ-compatible base64 subscription feeds."""

    def __init__(
        self,
        *,
        subscription_service: SubscriptionService,
        v2ray_service: V2RayProvisioningService,
        config: ClientSubscriptionConfig,
    ) -> None:
        self._subscription_service = subscription_service
        self._v2ray_service = v2ray_service
        self._config = config

    async def get_subscription_url_for_user(self, user_id: int) -> str:
        from vpn_core.subscription_domain.domain.queries import GetUserQuery

        user = await self._subscription_service.get_user(GetUserQuery(user_id=user_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user = await self._subscription_service.ensure_subscription_token(user)
        if not user.subscription_token:
            raise HTTPException(status_code=500, detail="Could not create subscription token")
        return self._config.build_url(user.subscription_token)

    async def render_subscription_feed(self, token: str) -> SubscriptionFeed:
        from vpn_core.subscription_domain.domain.queries import GetUserQuery

        user = await self._subscription_service.get_user(
            GetUserQuery(subscription_token=token.strip())
        )
        if not user or not user.is_active or user.is_blocked:
            raise HTTPException(status_code=404, detail="Subscription not found")

        now = datetime.now(UTC)
        subscriptions = await self._subscription_service.list_subscriptions(
            ListSubscriptionsQuery(user_id=user.id)
        )
        active_subscription_ids = {
            subscription.id
            for subscription in subscriptions
            if subscription.id is not None
            and subscription.service_type == "v2ray"
            and subscription.status == SubscriptionStatus.active
            and subscription.expire_at > now
            and (
                subscription.traffic_limit_bytes == 0
                or subscription.traffic_used_bytes < subscription.traffic_limit_bytes
            )
        }

        credentials = await self._v2ray_service.list_configs(user.id, active_only=True)
        links: list[str] = []
        seen: set[str] = set()
        total_limit = 0
        total_used = 0
        latest_expire: datetime | None = None

        for credential in credentials:
            if credential.status != V2RayConfigStatus.active:
                continue
            if credential.subscription_id not in active_subscription_ids:
                continue
            link = credential.vless_link.strip()
            if not self.is_valid_proxy_link(link) or link in seen:
                continue
            seen.add(link)
            links.append(link)

            subscription = next(
                (item for item in subscriptions if item.id == credential.subscription_id),
                None,
            )
            if subscription:
                total_used += subscription.traffic_used_bytes
                if subscription.traffic_limit_bytes > 0:
                    total_limit += subscription.traffic_limit_bytes
                if latest_expire is None or subscription.expire_at > latest_expire:
                    latest_expire = subscription.expire_at

        encoded_links = base64.b64encode("\n".join(links).encode("utf-8")).decode("ascii")
        expire_ts = int(latest_expire.timestamp()) if latest_expire else 0
        userinfo = f"upload=0; download={total_used}; total={total_limit}; expire={expire_ts}"
        headers = {
            "profile-update-interval": str(self._config.update_interval_hours),
            "subscription-userinfo": userinfo,
            "profile-title": self._config.profile_title,
            "content-disposition": f'inline; filename="{self._config.profile_title}.txt"',
        }
        return SubscriptionFeed(body=encoded_links, headers=headers, link_count=len(links))

    @staticmethod
    def is_valid_proxy_link(content: str) -> bool:
        return bool(content) and content.startswith(SUPPORTED_PROXY_SCHEMES)
