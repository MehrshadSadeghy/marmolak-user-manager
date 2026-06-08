from pydantic import BaseModel, Field

from vpn_core.openvpn_sync.domain.openvpn_user import OpenVpnUser


class ProvisionOpenVpnCommand(BaseModel):
    user_id: int
    server_id: int
    subscription_id: int | None = None
    config_count: int = Field(default=1, ge=1, le=10)


class DeactivateOpenVpnCommand(BaseModel):
    user_id: int
    subscription_id: int | None = None
    reason: str = "manual"


class ReportOpenVpnTrafficCommand(BaseModel):
    user_id: int
    subscription_id: int | None = None
    bytes_used: int = Field(..., ge=0)


class OpenVpnUserCommand(BaseModel):
    server_id: int
    user: OpenVpnUser
