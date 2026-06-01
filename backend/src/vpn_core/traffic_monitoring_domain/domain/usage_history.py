from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UsageHistory(BaseModel):
    """Historical usage record for reporting, debug, and behavior analysis."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    user_id: int
    subscription_id: int
    server_id: int | None = None
    used_bytes: int = Field(default=0, ge=0)
    recorded_at: datetime | None = None
    created_at: datetime | None = None
