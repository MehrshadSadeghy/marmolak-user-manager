import datetime
from typing import Optional, Any

from pydantic import BaseModel
from pydantic.types import Json
from uuid import UUID

class Strategy(BaseModel):
    id: UUID = None
    name: str
    data: dict[str, Any]
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True
