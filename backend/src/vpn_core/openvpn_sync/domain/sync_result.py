from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class SyncStatus(str, Enum):
    success = "success"
    skipped = "skipped"
    failed = "failed"


class SyncOperationResult(BaseModel):
    operation: str
    status: SyncStatus
    message: str = ""
    server_id: int | None = None
    common_name: str | None = None
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProvisioningResult(BaseModel):
    credentials: list
    results: list[SyncOperationResult] = Field(default_factory=list)
    idempotent: bool = False
    ephemeral_passwords: dict[str, str] = Field(default_factory=dict)
