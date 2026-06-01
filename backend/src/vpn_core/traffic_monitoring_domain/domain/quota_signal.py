import enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QuotaSignalType(str, enum.Enum):
    traffic_exceeded = "traffic_exceeded"
    approaching_limit = "approaching_limit"


class QuotaSignal(BaseModel):
    """Warning signal emitted when usage crosses a threshold — no enforcement here."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    user_id: int
    subscription_id: int
    uuid: str = Field(..., max_length=64)
    signal_type: QuotaSignalType
    used_bytes: int = Field(default=0, ge=0)
    limit_bytes: int = Field(default=0, ge=0)
    acknowledged: bool = False
    recorded_at: datetime | None = None
    created_at: datetime | None = None
