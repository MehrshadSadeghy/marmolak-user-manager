from vpn_core.server_management_domain.db_model.server import ServerORM
from vpn_core.server_management_domain.domain.capacity import ServerCapacity
from vpn_core.server_management_domain.domain.connection_info import ConnectionInfo
from vpn_core.server_management_domain.domain.openvpn_settings import OpenVpnSettings
from vpn_core.server_management_domain.domain.v2ray_settings import V2RaySettings
from vpn_core.server_management_domain.domain.resource_monitoring import ResourceMonitoring
from vpn_core.server_management_domain.domain.server import Server


def server_orm_to_domain(obj: ServerORM) -> Server:
    return Server(
        id=obj.id,
        name=obj.name,
        country_code=obj.country_code,
        city=obj.city,
        provider=obj.provider,
        cpu_cores=obj.cpu_cores,
        ram_mb=obj.ram_mb,
        disk_gb=obj.disk_gb,
        connection=ConnectionInfo(
            host=obj.host,
            ssh_port=obj.ssh_port,
            api_port=obj.api_port,
        ),
        capacity=ServerCapacity(
            max_users=obj.max_users,
            current_users=obj.current_users,
            max_bandwidth_mbps=obj.max_bandwidth_mbps,
        ),
        monitoring=ResourceMonitoring(
            cpu_usage=obj.cpu_usage,
            ram_usage=obj.ram_usage,
            disk_usage=obj.disk_usage,
            network_in=obj.network_in,
            network_out=obj.network_out,
        ),
        xray_inbound_tag=obj.xray_inbound_tag,
        openvpn=OpenVpnSettings(
            enabled=obj.openvpn_enabled,
            node_api_secret=obj.node_api_secret,
            vpn_host=obj.vpn_host,
            vpn_port=obj.vpn_port,
            vpn_proto=obj.vpn_proto,
        ),
        v2ray=V2RaySettings(
            enabled=obj.v2ray_enabled,
            node_api_secret=obj.v2ray_node_api_secret,
            node_api_port=obj.v2ray_node_api_port,
            vpn_host=obj.v2ray_vpn_host,
            vpn_port=obj.v2ray_vpn_port,
            ws_path=obj.v2ray_ws_path,
            network=obj.v2ray_network,
            security=obj.v2ray_security,
            sni=obj.v2ray_sni,
            fingerprint=obj.v2ray_fingerprint,
        ),
        status=obj.status,
        is_active=obj.is_active,
        last_health_check_at=obj.last_health_check_at,
        last_seen_at=obj.last_seen_at,
        notes=obj.notes,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def apply_domain_to_orm(server: Server, obj: ServerORM) -> None:
    obj.name = server.name
    obj.country_code = server.country_code.upper()
    obj.city = server.city
    obj.provider = server.provider
    obj.cpu_cores = server.cpu_cores
    obj.ram_mb = server.ram_mb
    obj.disk_gb = server.disk_gb
    obj.host = server.connection.host
    obj.ssh_port = server.connection.ssh_port
    obj.api_port = server.connection.api_port
    obj.max_users = server.capacity.max_users
    obj.current_users = server.capacity.current_users
    obj.max_bandwidth_mbps = server.capacity.max_bandwidth_mbps
    obj.cpu_usage = server.monitoring.cpu_usage
    obj.ram_usage = server.monitoring.ram_usage
    obj.disk_usage = server.monitoring.disk_usage
    obj.network_in = server.monitoring.network_in
    obj.network_out = server.monitoring.network_out
    obj.xray_inbound_tag = server.xray_inbound_tag
    obj.openvpn_enabled = server.openvpn.enabled
    obj.node_api_secret = server.openvpn.node_api_secret
    obj.vpn_host = server.openvpn.vpn_host
    obj.vpn_port = server.openvpn.vpn_port
    obj.vpn_proto = server.openvpn.vpn_proto
    obj.v2ray_enabled = server.v2ray.enabled
    obj.v2ray_node_api_secret = server.v2ray.node_api_secret
    obj.v2ray_node_api_port = server.v2ray.node_api_port
    obj.v2ray_vpn_host = server.v2ray.vpn_host
    obj.v2ray_vpn_port = server.v2ray.vpn_port
    obj.v2ray_ws_path = server.v2ray.ws_path
    obj.v2ray_network = server.v2ray.network
    obj.v2ray_security = server.v2ray.security
    obj.v2ray_sni = server.v2ray.sni
    obj.v2ray_fingerprint = server.v2ray.fingerprint
    obj.status = server.status
    obj.is_active = server.is_active
    obj.last_health_check_at = server.last_health_check_at
    obj.last_seen_at = server.last_seen_at
    obj.notes = server.notes
