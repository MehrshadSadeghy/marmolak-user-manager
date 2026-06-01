from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Plan(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    name: str
    description: str = ""
    duration_days: int
    traffic_limit_bytes: int
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
