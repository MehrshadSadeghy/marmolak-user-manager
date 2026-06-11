from pydantic import BaseModel, ConfigDict, Field


class ServerCapacity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    max_users: int = Field(default=100, ge=1)
    current_users: int = Field(default=0, ge=0)
    max_bandwidth_mbps: int = Field(..., ge=1)

    def is_full(self) -> bool:
        return self.current_users >= self.max_users

    def remaining_slots(self) -> int:
        return max(0, self.max_users - self.current_users)
