from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class V2RayConfigStatus(str, Enum):
    active = "active"
    disabled = "disabled"
    revoked = "revoked"
    expired = "expired"


class V2RayClientCredential(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    user_id: int
    subscription_id: int | None = None
    server_id: int
    telegram_id: str
    email: str
    client_uuid: str
    slot_index: int = 0
    vless_link: str
    status: V2RayConfigStatus = V2RayConfigStatus.active
    last_status_bytes: int = 0
    created_at: datetime | None = None
    revoked_at: datetime | None = None
