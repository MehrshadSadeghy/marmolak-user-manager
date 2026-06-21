from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException

from vpn_core.openvpn_sync.domain.auth_mode import OpenVpnAuthMode
from vpn_core.openvpn_sync.domain.openvpn_client_credential import OpenVpnClientCredential
from vpn_core.server_management_domain.domain.queries import GetServerQuery
from vpn_core.server_management_domain.service import ServerService
from vpn_core.subscription_domain.domain.subscription import Subscription


class OpenVpnCredentialDeliveryService:
    """Builds unified OpenVPN delivery payloads for every provisioning path."""

    def __init__(self, *, server_service: ServerService) -> None:
        self._server_service = server_service

    async def build_delivery(
        self,
        subscription: Subscription,
        credential: OpenVpnClientCredential,
        *,
        ephemeral_password: str | None = None,
        include_ovpn_file: bool = True,
    ) -> dict:
        server = await self._server_service.get_server(GetServerQuery(server_id=credential.server_id))
        if not server:
            raise HTTPException(status_code=404, detail="OpenVPN server not found")

        now = datetime.now(UTC)
        remaining_days = max((subscription.expire_at - now).days, 0)
        remaining_bytes = max(
            subscription.traffic_limit_bytes - subscription.traffic_used_bytes,
            0,
        )
        username = credential.vpn_username or credential.common_name
        auth_mode = credential.auth_mode.value
        server_host = server.openvpn.vpn_host or server.connection.host
        server_port = server.openvpn.vpn_port
        server_proto = server.openvpn.vpn_proto

        delivery = {
            "service_type": subscription.service_type,
            "subscription_id": subscription.id or 0,
            "delivery_type": "openvpn_package" if include_ovpn_file else "openvpn_credentials",
            "content": credential.ovpn_content if include_ovpn_file else "",
            "filename": f"{credential.common_name}.ovpn" if include_ovpn_file else None,
            "config_id": credential.common_name,
            "username": username,
            "password": ephemeral_password,
            "includes_password": bool(ephemeral_password),
            "server_host": server_host,
            "server_port": server_port,
            "server_proto": server_proto,
            "expire_at": subscription.expire_at.isoformat(),
            "traffic_limit_bytes": subscription.traffic_limit_bytes,
            "traffic_used_bytes": subscription.traffic_used_bytes,
            "remaining_bytes": remaining_bytes,
            "remaining_days": remaining_days,
            "auth_mode": auth_mode,
        }
        return delivery

    @staticmethod
    def uses_username_password_auth(delivery: dict) -> bool:
        auth_mode = delivery.get("auth_mode") or OpenVpnAuthMode.certificate.value
        return auth_mode in {
            OpenVpnAuthMode.dual.value,
            OpenVpnAuthMode.user_pass.value,
        }

    @staticmethod
    def format_telegram_message(delivery: dict, *, view_only: bool = False) -> str:
        username = delivery.get("username") or delivery.get("config_id") or "—"
        server_host = delivery.get("server_host") or "—"
        server_port = delivery.get("server_port") or "—"
        server_proto = (delivery.get("server_proto") or "udp").upper()
        remaining_days = delivery.get("remaining_days")
        remaining_bytes = delivery.get("remaining_bytes")
        limit_bytes = delivery.get("traffic_limit_bytes")
        used_bytes = delivery.get("traffic_used_bytes")

        title = "ℹ️ <b>اطلاعات اتصال OpenVPN</b>" if view_only else "🎉 <b>سرویس OpenVPN آماده است</b>"
        lines = [
            title,
            "",
            f"🆔 نام کاربری: <code>{username}</code>",
        ]

        if delivery.get("includes_password") and delivery.get("password"):
            lines.append(f"🔑 رمز عبور: <code>{delivery['password']}</code>")
            lines.append("⚠️ رمز را در جای امن ذخیره کن. فقط یک‌بار نمایش داده می‌شود.")
        elif not view_only and OpenVpnCredentialDeliveryService.uses_username_password_auth(delivery):
            lines.append("🔑 برای بازیابی رمز از دکمه «بازیابی رمز» استفاده کن.")

        lines.extend(
            [
                f"🖥 سرور: <code>{server_host}</code>",
                f"🔌 پورت/پروتکل: <code>{server_port}</code> ({server_proto})",
            ]
        )

        if remaining_days is not None:
            lines.append(f"📅 انقضا: <b>{remaining_days}</b> روز")
        if limit_bytes is not None and used_bytes is not None:
            lines.append(
                "📊 حجم: "
                f"<b>{OpenVpnCredentialDeliveryService._format_bytes(used_bytes)}</b> / "
                f"<b>{OpenVpnCredentialDeliveryService._format_bytes(limit_bytes)}</b>"
            )
        if remaining_bytes is not None:
            lines.append(
                f"📉 باقی‌مانده: <b>{OpenVpnCredentialDeliveryService._format_bytes(remaining_bytes)}</b>"
            )

        if not view_only and delivery.get("filename"):
            config_id = str(delivery["filename"]).removesuffix(".ovpn")
            lines.extend(["", f"📂 فایل کانفیگ: <code>{config_id}.ovpn</code>"])

        return "\n".join(lines)

    @staticmethod
    def _format_bytes(num_bytes: int) -> str:
        if num_bytes >= 1024**3:
            return f"{num_bytes / 1024**3:.2f} GB"
        if num_bytes >= 1024**2:
            return f"{num_bytes / 1024**2:.2f} MB"
        return f"{num_bytes} B"
