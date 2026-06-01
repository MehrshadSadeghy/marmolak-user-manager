from pydantic import BaseModel

from vpn_core.server_management_domain.domain.resource_monitoring import ResourceMonitoring
from vpn_core.server_management_domain.domain.server import ServerStatus


class UpdateServerStatusCommand(BaseModel):
    server_id: int
    status: ServerStatus


class UpdateResourceMonitoringCommand(BaseModel):
    server_id: int
    monitoring: ResourceMonitoring
