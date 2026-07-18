from enum import Enum

from pydantic import BaseModel

from vpn_core.v2ray_sync.domain.v2ray_client_credential import V2RayClientCredential


class SyncStatus(str, Enum):
    success = "success"
    failed = "failed"


class SyncOperationResult(BaseModel):
    operation: str
    status: SyncStatus
    message: str | None = None
    server_id: int | None = None
    email: str | None = None
    executed_at: str | None = None


class ProvisioningResult(BaseModel):
    credentials: list[V2RayClientCredential]
    results: list[SyncOperationResult]
    idempotent: bool = False
