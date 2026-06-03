from pydantic import BaseModel

from vpn_core.server_management_domain.domain.server import ServerStatus


class GetServerQuery(BaseModel):
    server_id: int


class ListServersQuery(BaseModel):
    country_code: str | None = None
    is_active: bool | None = None
    status: ServerStatus | None = None
    openvpn_enabled: bool | None = None
    openvpn_enabled: bool | None = None
