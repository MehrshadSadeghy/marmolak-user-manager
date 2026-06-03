from pydantic import BaseModel, Field


class OpenVpnUser(BaseModel):
    common_name: str = Field(..., max_length=255)
    telegram_id: str | None = None
