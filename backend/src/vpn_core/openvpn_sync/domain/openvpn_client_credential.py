from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from vpn_core.openvpn_sync.domain.auth_mode import OpenVpnAuthMode


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
    auth_mode: OpenVpnAuthMode = OpenVpnAuthMode.certificate
    vpn_username: str | None = None
    password_hash: str | None = None
    password_rotated_at: datetime | None = None
    auth_synced_at: datetime | None = None
    status: OpenVpnConfigStatus = OpenVpnConfigStatus.active
    last_status_bytes: int = 0
    created_at: datetime | None = None
    revoked_at: datetime | None = None
