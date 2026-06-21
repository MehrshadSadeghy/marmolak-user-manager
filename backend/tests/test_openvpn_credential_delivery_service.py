from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from vpn_core.openvpn_sync.domain.auth_mode import OpenVpnAuthMode
from vpn_core.openvpn_sync.domain.openvpn_client_credential import (
    OpenVpnClientCredential,
    OpenVpnConfigStatus,
)
from vpn_core.openvpn_sync.services.openvpn_credential_delivery_service import (
    OpenVpnCredentialDeliveryService,
)
from vpn_core.server_management_domain.domain.capacity import ServerCapacity
from vpn_core.server_management_domain.domain.connection_info import ConnectionInfo
from vpn_core.server_management_domain.domain.openvpn_settings import OpenVpnSettings
from vpn_core.server_management_domain.domain.server import Server
from vpn_core.subscription_domain.domain.subscription import Subscription, SubscriptionStatus


def _server() -> Server:
    return Server(
        id=1,
        name="node-1",
        country_code="DE",
        cpu_cores=2,
        ram_mb=2048,
        disk_gb=40,
        connection=ConnectionInfo(host="10.0.0.1", api_port=8090),
        capacity=ServerCapacity(max_bandwidth_mbps=1000),
        openvpn=OpenVpnSettings(
            enabled=True,
            node_api_secret="secret",
            vpn_host="vpn.example.com",
            vpn_port=1433,
            vpn_proto="udp",
        ),
    )


def _subscription() -> Subscription:
    return Subscription(
        id=7,
        user_id=42,
        plan_id=1,
        service_type="openvpn",
        uuid="550e8400-e29b-41d4-a716-446655440000",
        status=SubscriptionStatus.active,
        traffic_limit_bytes=10_000_000_000,
        traffic_used_bytes=1_000_000_000,
        expire_at=datetime.now(UTC) + timedelta(days=20),
    )


def _credential(*, auth_mode: OpenVpnAuthMode = OpenVpnAuthMode.dual) -> OpenVpnClientCredential:
    return OpenVpnClientCredential(
        user_id=42,
        subscription_id=7,
        server_id=1,
        telegram_id="123",
        common_name="0123456789",
        ovpn_content="<ca>test</ca><cert>x</cert>",
        auth_mode=auth_mode,
        vpn_username="0123456789",
        status=OpenVpnConfigStatus.active,
    )


@pytest.mark.asyncio
async def test_build_delivery_includes_server_metadata_and_password_once():
    server_service = AsyncMock()
    server_service.get_server.return_value = _server()
    delivery_service = OpenVpnCredentialDeliveryService(server_service=server_service)

    delivery = await delivery_service.build_delivery(
        _subscription(),
        _credential(),
        ephemeral_password="SecurePass123!",
    )

    assert delivery["username"] == "0123456789"
    assert delivery["password"] == "SecurePass123!"
    assert delivery["includes_password"] is True
    assert delivery["server_host"] == "vpn.example.com"
    assert delivery["server_port"] == 1433
    assert delivery["server_proto"] == "udp"
    assert 19 <= delivery["remaining_days"] <= 20
    assert delivery["delivery_type"] == "openvpn_package"


@pytest.mark.asyncio
async def test_build_delivery_view_mode_omits_ovpn_file():
    server_service = AsyncMock()
    server_service.get_server.return_value = _server()
    delivery_service = OpenVpnCredentialDeliveryService(server_service=server_service)

    delivery = await delivery_service.build_delivery(
        _subscription(),
        _credential(),
        include_ovpn_file=False,
    )

    assert delivery["delivery_type"] == "openvpn_credentials"
    assert delivery["content"] == ""
    assert delivery["includes_password"] is False
    assert delivery["password"] is None


def test_format_telegram_message_includes_password_only_when_requested():
    delivery = {
        "username": "0123456789",
        "password": "SecurePass123!",
        "includes_password": True,
        "server_host": "vpn.example.com",
        "server_port": 1433,
        "server_proto": "udp",
        "remaining_days": 10,
        "traffic_limit_bytes": 10_000_000_000,
        "traffic_used_bytes": 1_000_000_000,
        "remaining_bytes": 9_000_000_000,
        "auth_mode": "dual",
        "filename": "0123456789.ovpn",
    }
    message = OpenVpnCredentialDeliveryService.format_telegram_message(delivery)
    assert "SecurePass123!" in message
    assert "vpn.example.com" in message
    assert "1433" in message


def test_format_telegram_message_view_only_hides_password():
    delivery = {
        "username": "0123456789",
        "includes_password": False,
        "server_host": "vpn.example.com",
        "server_port": 1433,
        "server_proto": "udp",
        "remaining_days": 10,
        "traffic_limit_bytes": 10_000_000_000,
        "traffic_used_bytes": 0,
        "remaining_bytes": 10_000_000_000,
        "auth_mode": "dual",
    }
    message = OpenVpnCredentialDeliveryService.format_telegram_message(delivery, view_only=True)
    assert "SecurePass123!" not in message
    assert "0123456789" in message
