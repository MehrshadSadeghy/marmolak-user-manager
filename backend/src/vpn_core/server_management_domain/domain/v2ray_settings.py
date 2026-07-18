from pydantic import BaseModel, ConfigDict, Field


class V2RaySettings(BaseModel):
    """Per-server V2Ray node connection and client link defaults."""

    model_config = ConfigDict(from_attributes=True)

    enabled: bool = False
    node_api_secret: str | None = Field(default=None, max_length=256)
    node_api_port: int = Field(default=8092, ge=1, le=65535)
    vpn_host: str | None = Field(default=None, max_length=255)
    vpn_port: int = Field(default=443, ge=1, le=65535)
    ws_path: str = Field(default="/v2ray", max_length=255)
    network: str = Field(default="ws", max_length=16)
    security: str = Field(default="tls", max_length=16)
    sni: str | None = Field(default=None, max_length=255)
    fingerprint: str | None = Field(default="chrome", max_length=32)
