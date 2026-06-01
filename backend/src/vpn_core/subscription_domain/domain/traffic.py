from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TrafficUsage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    subscription_id: int
    server_id: int | None = None
    uuid: str
    upload_bytes: int = 0
    download_bytes: int = 0
    total_bytes: int = 0
    recorded_at: datetime | None = None
    interval_seconds: int = 60
    created_at: datetime | None = None
