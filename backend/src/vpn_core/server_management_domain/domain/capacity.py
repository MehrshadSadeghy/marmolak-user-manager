from pydantic import BaseModel, ConfigDict, Field


class ServerCapacity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    max_users: int = Field(default=100, ge=1)
    current_users: int = Field(default=0, ge=0)
    max_bandwidth_mbps: int = Field(..., ge=1)
