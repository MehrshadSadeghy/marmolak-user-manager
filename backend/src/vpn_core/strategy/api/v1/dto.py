

import json
from datetime import datetime
from typing import Any, Optional, Dict
from uuid import UUID

from pydantic import BaseModel, field_validator

from vpn_core.strategy.db.strategy import Strategy


def _parse_nested_json(data: Dict[str, Any]) -> Dict[str, Any]:
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            try:
                result[key] = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                result[key] = value
        else:
            result[key] = value
    return result


class BaseStrategyDTO(BaseModel):
    data: Dict[str, Any]

    @field_validator("data", mode="before")
    @classmethod
    def parse_nested_json_strings(cls, v: Any) -> Any:
        if isinstance(v, dict):
            return _parse_nested_json(v)
        return v


class StrategyGetResponseDTO(BaseModel):
    strategies: list[Strategy]

class StrategyUpsetResponseDTO(BaseModel):
    status: str


class StrategyRowDTO(BaseStrategyDTO):
    name: str


class StrategyResponseDTO(BaseModel):
    id: UUID
    name: str
    data: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime]


class StrategyUpdateDTO(BaseStrategyDTO):
    id: UUID
    name: str
