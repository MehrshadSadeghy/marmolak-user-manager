from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PasarguardPanelLink(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    user_id: int
    subscription_token: str
    panel_username: str
    subscription_url: str
    linked_at: datetime | None = None
