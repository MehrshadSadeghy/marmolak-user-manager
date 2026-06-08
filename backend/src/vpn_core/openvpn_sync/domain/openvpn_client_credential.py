from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class OpenVpnConfigStatus(str, Enum):
    active = "active"
    disabled = "disabled"
    revoked = "revoked"
    expired = "expired"


class OpenVpnClientCredential(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    user_id: int
    subscription_id: int | None = None
    server_id: int
    telegram_id: str
    common_name: str
    slot_index: int = 0
    ovpn_content: str
    status: OpenVpnConfigStatus = OpenVpnConfigStatus.active
    last_status_bytes: int = 0
    created_at: datetime | None = None
    revoked_at: datetime | None = None
