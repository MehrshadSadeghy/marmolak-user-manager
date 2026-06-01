from datetime import datetime

from pydantic import BaseModel, Field

from vpn_core.traffic_monitoring_domain.domain.traffic_sample import ConnectionType


class CollectTrafficCommand(BaseModel):
    uuid: str = Field(..., max_length=64)
    server_id: int
    upload_bytes: int = Field(default=0, ge=0)
    download_bytes: int = Field(default=0, ge=0)
    connection_type: ConnectionType = ConnectionType.unknown
    recorded_at: datetime | None = None


class AggregateTrafficCommand(BaseModel):
    uuid: str = Field(..., max_length=64)
    subscription_id: int | None = None
    server_id: int | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None


class EmitQuotaSignalCommand(BaseModel):
    user_id: int
    subscription_id: int
    uuid: str = Field(..., max_length=64)
    used_bytes: int = Field(..., ge=0)
    limit_bytes: int = Field(..., ge=0)
    approaching_threshold: float = Field(default=0.9, ge=0.0, le=1.0)


class AcknowledgeQuotaSignalCommand(BaseModel):
    signal_id: int
