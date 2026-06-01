from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RealtimeSnapshot(BaseModel):
    """Live server load and bandwidth snapshot."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    server_id: int
    active_users: int = Field(default=0, ge=0)
    bandwidth_mbps: float = Field(default=0.0, ge=0.0)
    upload_bps: int = Field(default=0, ge=0)
    download_bps: int = Field(default=0, ge=0)
    recorded_at: datetime | None = None
    created_at: datetime | None = None
