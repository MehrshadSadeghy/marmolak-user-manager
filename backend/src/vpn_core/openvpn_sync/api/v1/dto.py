from pydantic import BaseModel, Field

from vpn_core.openvpn_sync.domain.commands import (
    DeactivateOpenVpnCommand,
    ProvisionOpenVpnCommand,
    ReportOpenVpnTrafficCommand,
)
from vpn_core.openvpn_sync.domain.openvpn_client_credential import OpenVpnClientCredential
from vpn_core.openvpn_sync.domain.sync_result import SyncOperationResult


class ProvisionOpenVpnDTO(BaseModel):
    user_id: int
    server_id: int
    subscription_id: int | None = None
    config_count: int = Field(default=1, ge=1, le=10)

    def to_command(self) -> ProvisionOpenVpnCommand:
        return ProvisionOpenVpnCommand(
            user_id=self.user_id,
            server_id=self.server_id,
            subscription_id=self.subscription_id,
            config_count=self.config_count,
        )


class DeactivateOpenVpnDTO(BaseModel):
    user_id: int
    reason: str = "manual"

    def to_command(self) -> DeactivateOpenVpnCommand:
        return DeactivateOpenVpnCommand(user_id=self.user_id, reason=self.reason)


class ReportTrafficDTO(BaseModel):
    user_id: int
    subscription_id: int | None = None
    bytes_used: int = Field(..., ge=0)

    def to_command(self) -> ReportOpenVpnTrafficCommand:
        return ReportOpenVpnTrafficCommand(
            user_id=self.user_id,
            subscription_id=self.subscription_id,
            bytes_used=self.bytes_used,
        )


class OpenVpnCredentialDTO(BaseModel):
    id: int
    user_id: int
    server_id: int
    telegram_id: str
    common_name: str
    slot_index: int
    status: str
    ovpn_content: str

    @classmethod
    def from_domain(cls, cred: OpenVpnClientCredential) -> "OpenVpnCredentialDTO":
        return cls(
            id=cred.id,
            user_id=cred.user_id,
            server_id=cred.server_id,
            telegram_id=cred.telegram_id,
            common_name=cred.common_name,
            slot_index=cred.slot_index,
            status=cred.status.value,
            ovpn_content=cred.ovpn_content,
        )


class ProvisionOpenVpnResponseDTO(BaseModel):
    configs: list[OpenVpnCredentialDTO]
    results: list[SyncOperationResult]
    idempotent: bool


class OpenVpnConfigListResponseDTO(BaseModel):
    configs: list[OpenVpnCredentialDTO]


class DeactivateOpenVpnResponseDTO(BaseModel):
    revoked_count: int
    reason: str


class TrafficReportResponseDTO(BaseModel):
    user_id: int
    bytes_used: int
    total_bytes: int
