from pydantic import BaseModel, ConfigDict, Field


class ConnectionInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    host: str = Field(..., max_length=255, description="Server IP address or domain")
    ssh_port: int = Field(default=22, ge=1, le=65535)
    api_port: int = Field(..., ge=1, le=65535, description="Xray/management API port")
