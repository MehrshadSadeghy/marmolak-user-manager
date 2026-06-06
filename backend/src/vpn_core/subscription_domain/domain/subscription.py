import enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SubscriptionStatus(str, enum.Enum):
    active = "active"
    expired = "expired"
    traffic_exceeded = "traffic_exceeded"
    disabled = "disabled"


class Subscription(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    user_id: int
    plan_id: int
    service_type: str
    uuid: str
    status: SubscriptionStatus = SubscriptionStatus.active
    traffic_limit_bytes: int = 0
    traffic_used_bytes: int = 0
    started_at: datetime | None = None
    expire_at: datetime
    created_at: datetime | None = None
    updated_at: datetime | None = None
