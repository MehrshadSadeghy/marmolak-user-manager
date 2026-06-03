from pydantic import BaseModel, Field

from vpn_core.server_management_domain.domain.capacity import ServerCapacity
from vpn_core.server_management_domain.domain.commands import (
    UpdateResourceMonitoringCommand,
    UpdateServerStatusCommand,
)
from vpn_core.server_management_domain.domain.connection_info import ConnectionInfo
from vpn_core.server_management_domain.domain.queries import GetServerQuery, ListServersQuery
from vpn_core.server_management_domain.domain.openvpn_settings import OpenVpnSettings
from vpn_core.server_management_domain.domain.resource_monitoring import ResourceMonitoring
from vpn_core.server_management_domain.domain.server import Server, ServerStatus


class ConnectionInfoDTO(BaseModel):
    host: str = Field(..., max_length=255)
    ssh_port: int = Field(default=22, ge=1, le=65535)
    api_port: int = Field(..., ge=1, le=65535)

    def to_domain(self) -> ConnectionInfo:
        return ConnectionInfo(
            host=self.host,
            ssh_port=self.ssh_port,
            api_port=self.api_port,
        )


class ServerCapacityDTO(BaseModel):
    max_users: int = Field(default=100, ge=1)
    current_users: int = Field(default=0, ge=0)
    max_bandwidth_mbps: int = Field(..., ge=1)

    def to_domain(self) -> ServerCapacity:
        return ServerCapacity(
            max_users=self.max_users,
            current_users=self.current_users,
            max_bandwidth_mbps=self.max_bandwidth_mbps,
        )


class OpenVpnSettingsDTO(BaseModel):
    enabled: bool = False
    node_api_secret: str | None = Field(default=None, max_length=256)
    vpn_host: str | None = Field(default=None, max_length=255)
    vpn_port: int = Field(default=1194, ge=1, le=65535)
    vpn_proto: str = Field(default="udp", max_length=16)

    def to_domain(self) -> OpenVpnSettings:
        return OpenVpnSettings(
            enabled=self.enabled,
            node_api_secret=self.node_api_secret,
            vpn_host=self.vpn_host,
            vpn_port=self.vpn_port,
            vpn_proto=self.vpn_proto,
        )


class ResourceMonitoringDTO(BaseModel):
    cpu_usage: float = Field(default=0.0, ge=0.0, le=100.0)
    ram_usage: float = Field(default=0.0, ge=0.0, le=100.0)
    disk_usage: float = Field(default=0.0, ge=0.0, le=100.0)
    network_in: int = Field(default=0, ge=0)
    network_out: int = Field(default=0, ge=0)

    def to_domain(self) -> ResourceMonitoring:
        return ResourceMonitoring(
            cpu_usage=self.cpu_usage,
            ram_usage=self.ram_usage,
            disk_usage=self.disk_usage,
            network_in=self.network_in,
            network_out=self.network_out,
        )


class CreateServerDTO(BaseModel):
    name: str = Field(..., max_length=128)
    country_code: str = Field(..., min_length=2, max_length=2)
    city: str | None = Field(default=None, max_length=128)
    provider: str | None = Field(default=None, max_length=128)

    cpu_cores: int = Field(..., ge=1)
    ram_mb: int = Field(..., ge=512)
    disk_gb: int = Field(..., ge=1)

    connection: ConnectionInfoDTO
    capacity: ServerCapacityDTO
    monitoring: ResourceMonitoringDTO = Field(default_factory=ResourceMonitoringDTO)

    xray_inbound_tag: str | None = Field(default=None, max_length=64)
    openvpn: OpenVpnSettingsDTO = Field(default_factory=OpenVpnSettingsDTO)
    status: ServerStatus = ServerStatus.offline
    is_active: bool = True
    notes: str | None = Field(default=None, max_length=1024)

    def to_domain(self) -> Server:
        return Server(
            name=self.name,
            country_code=self.country_code,
            city=self.city,
            provider=self.provider,
            cpu_cores=self.cpu_cores,
            ram_mb=self.ram_mb,
            disk_gb=self.disk_gb,
            connection=self.connection.to_domain(),
            capacity=self.capacity.to_domain(),
            monitoring=self.monitoring.to_domain(),
            xray_inbound_tag=self.xray_inbound_tag,
            openvpn=self.openvpn.to_domain(),
            status=self.status,
            is_active=self.is_active,
            notes=self.notes,
        )


class UpdateServerDTO(BaseModel):
    name: str = Field(..., max_length=128)
    country_code: str = Field(..., min_length=2, max_length=2)
    city: str | None = Field(default=None, max_length=128)
    provider: str | None = Field(default=None, max_length=128)

    cpu_cores: int = Field(..., ge=1)
    ram_mb: int = Field(..., ge=512)
    disk_gb: int = Field(..., ge=1)

    connection: ConnectionInfoDTO
    capacity: ServerCapacityDTO
    monitoring: ResourceMonitoringDTO

    xray_inbound_tag: str | None = Field(default=None, max_length=64)
    openvpn: OpenVpnSettingsDTO = Field(default_factory=OpenVpnSettingsDTO)
    status: ServerStatus
    is_active: bool = True
    notes: str | None = Field(default=None, max_length=1024)

    def to_domain(self, server_id: int) -> Server:
        return Server(
            id=server_id,
            name=self.name,
            country_code=self.country_code,
            city=self.city,
            provider=self.provider,
            cpu_cores=self.cpu_cores,
            ram_mb=self.ram_mb,
            disk_gb=self.disk_gb,
            connection=self.connection.to_domain(),
            capacity=self.capacity.to_domain(),
            monitoring=self.monitoring.to_domain(),
            xray_inbound_tag=self.xray_inbound_tag,
            openvpn=self.openvpn.to_domain(),
            status=self.status,
            is_active=self.is_active,
            notes=self.notes,
        )


class UpdateServerStatusDTO(BaseModel):
    status: ServerStatus

    def to_domain(self, server_id: int) -> UpdateServerStatusCommand:
        return UpdateServerStatusCommand(
            server_id=server_id,
            status=self.status,
        )


class UpdateResourceMonitoringDTO(BaseModel):
    monitoring: ResourceMonitoringDTO

    def to_domain(self, server_id: int) -> UpdateResourceMonitoringCommand:
        return UpdateResourceMonitoringCommand(
            server_id=server_id,
            monitoring=self.monitoring.to_domain(),
        )


class ServerResponseDTO(BaseModel):
    server: Server


class ServerListResponseDTO(BaseModel):
    servers: list[Server]


class DeleteServerResponseDTO(BaseModel):
    deleted: bool


class GetServerQueryDTO(BaseModel):
    server_id: int

    def to_domain(self) -> GetServerQuery:
        return GetServerQuery(server_id=self.server_id)


class ListServersQueryDTO(BaseModel):
    country_code: str | None = None
    is_active: bool | None = None
    status: ServerStatus | None = None
    openvpn_enabled: bool | None = None

    def to_domain(self) -> ListServersQuery:
        return ListServersQuery(
            country_code=self.country_code,
            is_active=self.is_active,
            status=self.status,
            openvpn_enabled=self.openvpn_enabled,
        )
