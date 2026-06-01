from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HealthMetric(BaseModel):
    """Point-in-time server health reading."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    server_id: int
    cpu_usage: float = Field(default=0.0, ge=0.0, le=100.0)
    ram_usage: float = Field(default=0.0, ge=0.0, le=100.0)
    disk_usage: float = Field(default=0.0, ge=0.0, le=100.0)
    latency_ms: float = Field(default=0.0, ge=0.0)
    recorded_at: datetime | None = None
    created_at: datetime | None = None
