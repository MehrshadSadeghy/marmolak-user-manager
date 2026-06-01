from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TrafficAggregation(BaseModel):
    """Aggregated consumption derived from raw samples."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    uuid: str = Field(..., max_length=64)
    subscription_id: int | None = None
    server_id: int | None = None
    upload_bytes: int = Field(default=0, ge=0)
    download_bytes: int = Field(default=0, ge=0)
    total_bytes: int = Field(default=0, ge=0)
    period_start: datetime | None = None
    period_end: datetime | None = None
    created_at: datetime | None = None
