import enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from vpn_core.traffic_monitoring_domain.domain.traffic_sample import ConnectionType


class ConnectionEvent(str, enum.Enum):
    connect = "connect"
    disconnect = "disconnect"
    fail = "fail"
    reconnect = "reconnect"


class ConnectionLog(BaseModel):
    """Connection lifecycle event log."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    uuid: str = Field(..., max_length=64)
    user_id: int | None = None
    subscription_id: int | None = None
    server_id: int
    event: ConnectionEvent
    connection_type: ConnectionType = ConnectionType.unknown
    recorded_at: datetime | None = None
    created_at: datetime | None = None
