from datetime import datetime

from pydantic import BaseModel, ConfigDict


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    telegram_id: str
    chat_id: str
    is_active: bool = True
    created_at: datetime | None = None
