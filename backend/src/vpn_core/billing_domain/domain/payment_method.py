from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PaymentMethod(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    name: str
    instructions: str
    is_active: bool = True
    sort_order: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
