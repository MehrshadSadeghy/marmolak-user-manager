from pydantic import BaseModel, Field

from vpn_core.v2ray_sync.domain.v2ray_user import V2RayUser


class ProvisionV2RayCommand(BaseModel):
    user_id: int
    server_id: int
    subscription_id: int | None = None
    config_count: int = Field(default=1, ge=1, le=10)


class DeactivateV2RayCommand(BaseModel):
    user_id: int
    subscription_id: int | None = None
    reason: str = "manual"
