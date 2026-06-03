from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OpenVpnTrafficUsage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    user_id: int
    subscription_id: int | None = None
    bytes_used: int = 0
    recorded_at: datetime | None = None
