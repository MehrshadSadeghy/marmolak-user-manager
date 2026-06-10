from pydantic import BaseModel, ConfigDict, Field


class OpenVpnSettings(BaseModel):
    """Per-server OpenVPN node (vpn-node) connection and profile defaults."""

    model_config = ConfigDict(from_attributes=True)

    enabled: bool = False
    node_api_secret: str | None = Field(default=None, max_length=256)
    vpn_host: str | None = Field(default=None, max_length=255)
    vpn_port: int = Field(default=1433, ge=1, le=65535)
    vpn_proto: str = Field(default="udp", max_length=16)
