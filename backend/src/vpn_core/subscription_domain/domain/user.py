from datetime import datetime

from pydantic import BaseModel, ConfigDict


class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    telegram_id: str
    chat_id: str
    username: str | None = None
    is_active: bool = True
    is_blocked: bool = False
    blocked_at: datetime | None = None
    blocked_reason: str | None = None
    blocked_by_admin_telegram_id: str | None = None
    is_collaborator: bool = False
    created_at: datetime | None = None
