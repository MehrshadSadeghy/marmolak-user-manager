import enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConnectionType(str, enum.Enum):
    vmess = "vmess"
    vless = "vless"
    trojan = "trojan"
    shadowsocks = "shadowsocks"
    unknown = "unknown"


class TrafficSample(BaseModel):
    """Raw traffic reading collected from Xray — collect only, no decisions."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    uuid: str = Field(..., max_length=64)
    server_id: int
    upload_bytes: int = Field(default=0, ge=0)
    download_bytes: int = Field(default=0, ge=0)
    connection_type: ConnectionType = ConnectionType.unknown
    recorded_at: datetime | None = None
    created_at: datetime | None = None
