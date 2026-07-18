import enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from vpn_core.server_management_domain.domain.capacity import ServerCapacity
from vpn_core.server_management_domain.domain.connection_info import ConnectionInfo
from vpn_core.server_management_domain.domain.openvpn_settings import OpenVpnSettings
from vpn_core.server_management_domain.domain.v2ray_settings import V2RaySettings
from vpn_core.server_management_domain.domain.resource_monitoring import ResourceMonitoring


class ServerStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    degraded = "degraded"


class Server(BaseModel):
    """VPN node identity used across router, service, and repository layers."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None

    name: str = Field(..., max_length=128)
    country_code: str = Field(..., min_length=2, max_length=2)
    city: str | None = Field(default=None, max_length=128)
    provider: str | None = Field(default=None, max_length=128)

    cpu_cores: int = Field(..., ge=1)
    ram_mb: int = Field(..., ge=512)
    disk_gb: int = Field(..., ge=1)

    connection: ConnectionInfo
    capacity: ServerCapacity
    monitoring: ResourceMonitoring = Field(default_factory=ResourceMonitoring)

    xray_inbound_tag: str | None = Field(default=None, max_length=64)
    openvpn: OpenVpnSettings = Field(default_factory=OpenVpnSettings)
    v2ray: V2RaySettings = Field(default_factory=V2RaySettings)

    status: ServerStatus = ServerStatus.offline
    is_active: bool = True

    last_health_check_at: datetime | None = None
    last_seen_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=1024)

    created_at: datetime | None = None
    updated_at: datetime | None = None
