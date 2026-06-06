from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BotSettings(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    support_username: str | None = None
    payment_instructions: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
