from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ServiceType(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    slug: str
    display_name: str
    description: str = ""
    is_enabled: bool = True
    sort_order: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
