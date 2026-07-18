import pytest

from vpn_core.server_management_domain.domain.capacity import ServerCapacity
from vpn_core.server_management_domain.domain.connection_info import ConnectionInfo
from vpn_core.server_management_domain.domain.openvpn_settings import OpenVpnSettings
from vpn_core.server_management_domain.domain.server import Server
from vpn_core.server_management_domain.domain.v2ray_settings import V2RaySettings
from vpn_core.v2ray_sync.services.helpers import generate_config_id, node_api_configured


def _server(*, name: str, v2ray_enabled: bool = False, xray_tag: str | None = None) -> Server:
    return Server(
        name=name,
        country_code="US",
        cpu_cores=2,
        ram_mb=2048,
        disk_gb=40,
        connection=ConnectionInfo(host="10.0.0.1", api_port=8090),
        capacity=ServerCapacity(max_bandwidth_mbps=1000),
        xray_inbound_tag=xray_tag,
        v2ray=V2RaySettings(
            enabled=v2ray_enabled,
            node_api_secret="secret" if v2ray_enabled else None,
            vpn_host="vpn.example.com",
        ),
    )


def test_generate_config_id_is_ten_digits():
    config_id = generate_config_id()
    assert len(config_id) == 10
    assert config_id.isdigit()


def test_v2ray_node_api_configured():
    v2ray_server = _server(name="V2", v2ray_enabled=True, xray_tag="inbound-vless")
    openvpn_only = _server(name="openvpn_only", v2ray_enabled=False)

    assert node_api_configured(v2ray_server) is True
    assert node_api_configured(openvpn_only) is False
