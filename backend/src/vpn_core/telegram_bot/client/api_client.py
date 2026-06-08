from __future__ import annotations

from typing import Any

import httpx


class UserManagerApiClient:
    def __init__(self, base_url: str, bot_api_key: str):
        self._base_url = base_url.rstrip("/")
        self._headers = {"X-Bot-Api-Key": bot_api_key}

    def _admin_headers(self, admin_telegram_id: str) -> dict[str, str]:
        headers = dict(self._headers)
        headers["X-Admin-Telegram-Id"] = admin_telegram_id
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        admin_telegram_id: str | None = None,
    ) -> Any:
        headers = self._admin_headers(admin_telegram_id) if admin_telegram_id else self._headers
        timeout = 120.0 if path.endswith("/openvpn-endpoint") else 60.0
        async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
            response = await client.request(method, f"{self._base_url}{path}", json=json)
            response.raise_for_status()
            if response.content:
                return response.json()
            return None

    async def register_user(self, telegram_id: str, chat_id: str, username: str | None) -> dict:
        return await self._request(
            "POST",
            "/api/v1/bot/users/register",
            json={
                "telegram_id": telegram_id,
                "chat_id": chat_id,
                "username": username,
            },
        )

    async def list_services(self) -> list[dict]:
        data = await self._request("GET", "/api/v1/bot/services")
        return data["services"]

    async def list_plans(self, service_type: str) -> list[dict]:
        data = await self._request("GET", f"/api/v1/bot/services/{service_type}/plans")
        return data["plans"]

    async def preview_purchase(self, telegram_id: str, plan_id: int) -> dict:
        return await self._request(
            "POST",
            "/api/v1/bot/purchase/preview",
            json={"telegram_id": telegram_id, "plan_id": plan_id},
        )

    async def purchase(self, telegram_id: str, plan_id: int) -> dict:
        return await self._request(
            "POST",
            "/api/v1/bot/purchase",
            json={"telegram_id": telegram_id, "plan_id": plan_id},
        )

    async def initiate_payment(self, payload: dict) -> dict:
        return await self._request("POST", "/api/v1/bot/payments/initiate", json=payload)

    async def get_active_payment(self, telegram_id: str) -> dict:
        return await self._request("GET", f"/api/v1/bot/users/{telegram_id}/payments/active")

    async def submit_receipt(self, payment_request_id: int, payload: dict) -> dict:
        return await self._request(
            "POST",
            f"/api/v1/bot/payments/{payment_request_id}/receipt",
            json=payload,
        )

    async def renew(self, telegram_id: str, subscription_id: int, plan_id: int) -> dict:
        return await self._request(
            "POST",
            "/api/v1/bot/renew",
            json={
                "telegram_id": telegram_id,
                "subscription_id": subscription_id,
                "plan_id": plan_id,
            },
        )


    async def list_payment_methods(self) -> list[dict]:
        data = await self._request("GET", "/api/v1/bot/payment-methods")
        return data["payment_methods"]

    async def list_user_services(self, telegram_id: str) -> list[dict]:
        data = await self._request("GET", f"/api/v1/bot/users/{telegram_id}/services")
        return data["services"]

    async def get_subscription_delivery(self, telegram_id: str, subscription_id: int) -> dict:
        return await self._request(
            "GET",
            f"/api/v1/bot/users/{telegram_id}/subscriptions/{subscription_id}/delivery",
        )

    async def get_openvpn_config_delivery(self, telegram_id: str, config_id: str) -> dict:
        return await self._request(
            "GET",
            f"/api/v1/bot/users/{telegram_id}/openvpn/configs/{config_id}/delivery",
        )

    async def get_support(self) -> dict:
        return await self._request("GET", "/api/v1/bot/support")

    async def initiate_topup(self, telegram_id: str, amount_toman: int) -> dict:
        return await self._request(
            "POST",
            "/api/v1/bot/wallet/topup/initiate",
            json={"telegram_id": telegram_id, "amount_toman": amount_toman},
        )

    async def get_wallet(self, telegram_id: str) -> dict:
        return await self._request("GET", f"/api/v1/bot/users/{telegram_id}/wallet")

    async def get_openvpn_config_traffic(self, telegram_id: str, config_id: str) -> dict:
        return await self._request(
            "POST",
            "/api/v1/bot/openvpn/config-traffic",
            json={"telegram_id": telegram_id, "config_id": config_id},
        )

    async def list_pending_payments(self, admin_telegram_id: str) -> list[dict]:
        data = await self._request(
            "GET",
            "/api/v1/admin/bot/payments/pending",
            admin_telegram_id=admin_telegram_id,
        )
        return data["payments"]

    async def approve_payment(self, admin_telegram_id: str, payment_request_id: int) -> dict:
        return await self._request(
            "POST",
            f"/api/v1/admin/bot/payments/{payment_request_id}/approve",
            json={"admin_note": ""},
            admin_telegram_id=admin_telegram_id,
        )

    async def reject_payment(self, admin_telegram_id: str, payment_request_id: int) -> dict:
        return await self._request(
            "POST",
            f"/api/v1/admin/bot/payments/{payment_request_id}/reject",
            json={"admin_note": ""},
            admin_telegram_id=admin_telegram_id,
        )

    async def list_service_types_admin(self, admin_telegram_id: str) -> list[dict]:
        data = await self._request(
            "GET",
            "/api/v1/admin/commerce/service-types",
            admin_telegram_id=admin_telegram_id,
        )
        return data["service_types"]

    async def toggle_service_type(self, admin_telegram_id: str, slug: str, enable: bool) -> dict:
        action = "enable" if enable else "disable"
        return await self._request(
            "POST",
            f"/api/v1/admin/commerce/service-types/{slug}/{action}",
            admin_telegram_id=admin_telegram_id,
        )

    async def list_plans_admin(self, admin_telegram_id: str) -> list[dict]:
        data = await self._request(
            "GET",
            "/api/v1/admin/subscription/plans",
            admin_telegram_id=admin_telegram_id,
        )
        return data["plans"]
    async def create_plan_admin(self, admin_telegram_id: str, payload: dict) -> dict:
        data = await self._request(
            "POST",
            "/api/v1/admin/subscription/plans",
            json=payload,
            admin_telegram_id=admin_telegram_id,
        )
        return data["plan"]

    async def list_payment_methods_admin(self, admin_telegram_id: str) -> list[dict]:
        data = await self._request(
            "GET",
            "/api/v1/admin/billing/payment-methods",
            admin_telegram_id=admin_telegram_id,
        )
        return data["payment_methods"]

    async def create_payment_method_admin(self, admin_telegram_id: str, payload: dict) -> dict:
        data = await self._request(
            "POST",
            "/api/v1/admin/billing/payment-methods",
            json=payload,
            admin_telegram_id=admin_telegram_id,
        )
        return data["payment_method"]

    async def update_payment_method_admin(
        self,
        admin_telegram_id: str,
        method_id: int,
        payload: dict,
    ) -> dict:
        data = await self._request(
            "PATCH",
            f"/api/v1/admin/billing/payment-methods/{method_id}",
            json=payload,
            admin_telegram_id=admin_telegram_id,
        )
        return data["payment_method"]

    async def delete_payment_method_admin(self, admin_telegram_id: str, method_id: int) -> dict:
        return await self._request(
            "DELETE",
            f"/api/v1/admin/billing/payment-methods/{method_id}",
            admin_telegram_id=admin_telegram_id,
        )

    async def get_financial_report_admin(self, admin_telegram_id: str, period: str) -> dict:
        data = await self._request(
            "GET",
            f"/api/v1/admin/billing/reports/financial?period={period}",
            admin_telegram_id=admin_telegram_id,
        )
        return data["report"]

    async def list_openvpn_servers_admin(self, admin_telegram_id: str) -> list[dict]:
        data = await self._request(
            "GET",
            "/api/v1/admin/bot/servers/openvpn",
            admin_telegram_id=admin_telegram_id,
        )
        return data["servers"]

    async def apply_openvpn_endpoint_admin(
        self,
        admin_telegram_id: str,
        server_id: int,
        port: int,
        proto: str,
    ) -> dict:
        return await self._request(
            "POST",
            f"/api/v1/admin/bot/servers/{server_id}/openvpn-endpoint",
            json={"port": port, "proto": proto},
            admin_telegram_id=admin_telegram_id,
        )
