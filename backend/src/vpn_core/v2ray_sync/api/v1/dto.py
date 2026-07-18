from pydantic import BaseModel, Field

from vpn_core.v2ray_sync.domain.commands import DeactivateV2RayCommand, ProvisionV2RayCommand
from vpn_core.v2ray_sync.domain.sync_result import SyncOperationResult
from vpn_core.v2ray_sync.domain.v2ray_client_credential import V2RayClientCredential


class ProvisionV2RayDTO(BaseModel):
    user_id: int
    server_id: int
    subscription_id: int | None = None
    config_count: int = Field(default=1, ge=1, le=10)

    def to_command(self) -> ProvisionV2RayCommand:
        return ProvisionV2RayCommand(
            user_id=self.user_id,
            server_id=self.server_id,
            subscription_id=self.subscription_id,
            config_count=self.config_count,
        )


class DeactivateV2RayDTO(BaseModel):
    user_id: int
    reason: str = "manual"
    subscription_id: int | None = None

    def to_command(self) -> DeactivateV2RayCommand:
        return DeactivateV2RayCommand(
            user_id=self.user_id,
            reason=self.reason,
            subscription_id=self.subscription_id,
        )


class V2RayCredentialDTO(BaseModel):
    id: int
    user_id: int
    server_id: int
    telegram_id: str
    email: str
    client_uuid: str
    slot_index: int
    status: str
    vless_link: str

    @classmethod
    def from_domain(cls, cred: V2RayClientCredential) -> "V2RayCredentialDTO":
        return cls(
            id=cred.id,
            user_id=cred.user_id,
            server_id=cred.server_id,
            telegram_id=cred.telegram_id,
            email=cred.email,
            client_uuid=cred.client_uuid,
            slot_index=cred.slot_index,
            status=cred.status.value,
            vless_link=cred.vless_link,
        )


class ProvisionV2RayResponseDTO(BaseModel):
    configs: list[V2RayCredentialDTO]
    results: list[SyncOperationResult]
    idempotent: bool


class V2RayConfigListResponseDTO(BaseModel):
    configs: list[V2RayCredentialDTO]


class DeactivateV2RayResponseDTO(BaseModel):
    revoked_count: int
    reason: str
